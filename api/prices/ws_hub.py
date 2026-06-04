import asyncio
import logging
import math
from typing import Any, Optional

from fastapi import WebSocket

from api.data.local import (
    PRICE_CACHE,
    PREV_CLOSE_CACHE,
    DAY_CHANGE_CACHE,
    DAY_CHANGE_PCT_CACHE,
)
from api.data import utils as data_utils
from api.data import red

logger = logging.getLogger(__name__)


def _compute_day_change(price: float, prev_close: Optional[float]):
    """Return (day_change, day_change_pct) or (None, None) if prev_close missing/zero."""
    if prev_close and math.isfinite(prev_close) and prev_close != 0:
        change = round(price - prev_close, 4)
        pct    = round((price - prev_close) / prev_close * 100, 4)
        return change, pct
    return None, None


def _build_tick(instrument_id: str, price: float, ts=None, source=None) -> dict:
    """Build a complete price tick including pre-computed day change fields."""
    prev_close     = PREV_CLOSE_CACHE.get(instrument_id)
    day_change     = DAY_CHANGE_CACHE.get(instrument_id)
    day_change_pct = DAY_CHANGE_PCT_CACHE.get(instrument_id)
    return {
        "type":           "price",
        "instrument_id":  instrument_id,
        "price":          price,
        "previous_close": prev_close,
        "day_change":     day_change,
        "day_change_pct": day_change_pct,
        "ts":             ts,
        "source":         source,
    }


class PriceWebSocketHub:
    # Known Upstox instrument-key segment prefixes.
    # If the instrument_id already contains "|" with one of these prefixes it is
    # already a valid Upstox key and can be forwarded directly to the pricefeed.
    _UPSTOX_KEY_PREFIXES = frozenset({
        "NSE_EQ", "NSE_FO", "NSE_INDEX", "NSE_COM",
        "BSE_EQ", "BSE_FO", "BSE_INDEX",
        "MCX_FO", "NCD_FO", "BCD_FO",
    })

    def __init__(self) -> None:
        self._subscriptions: dict[WebSocket, set[str]] = {}
        self._feed_connections: set[WebSocket] = set()
        self._runtime_subscriptions: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._subscriptions[websocket] = set()

    async def disconnect(self, websocket: WebSocket) -> None:
        should_sync = False
        async with self._lock:
            if websocket in self._subscriptions and websocket not in self._feed_connections:
                should_sync = True
            self._subscriptions.pop(websocket, None)
            self._feed_connections.discard(websocket)
        if should_sync:
            await self._sync_feed_subscriptions()

    async def handle(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        action = str(message.get("action", "")).strip().lower()

        # ── register_feed ───────────────────────────────────────────────────────
        if action == "register_feed":
            async with self._lock:
                self._feed_connections.add(websocket)
            await websocket.send_json({"type": "ack", "action": "register_feed"})
            await self._sync_feed_subscriptions()
            return

        # ── subscribe ───────────────────────────────────────────────────────────
        if action == "subscribe":
            instrument_ids = {
                str(iid)
                for iid in (message.get("instrument_ids") or [])
                if iid is not None
            }
            async with self._lock:
                current = self._subscriptions.get(websocket, set())
                current.update(instrument_ids)
                self._subscriptions[websocket] = current
            await self._sync_feed_subscriptions()

            # Send cached snapshot (with day change) for each subscribed instrument
            for instrument_id in instrument_ids:
                if instrument_id in PRICE_CACHE:
                    tick = _build_tick(instrument_id, PRICE_CACHE[instrument_id], source="cache")
                    await websocket.send_json(tick)

            await websocket.send_json({
                "type": "ack",
                "action": "subscribe",
                "instrument_ids": sorted(instrument_ids),
            })
            return

        # ── unsubscribe ─────────────────────────────────────────────────────────
        if action == "unsubscribe":
            instrument_ids = {
                str(iid)
                for iid in (message.get("instrument_ids") or [])
                if iid is not None
            }
            async with self._lock:
                current = self._subscriptions.get(websocket, set())
                current.difference_update(instrument_ids)
                self._subscriptions[websocket] = current
            await self._sync_feed_subscriptions()
            await websocket.send_json({
                "type": "ack",
                "action": "unsubscribe",
                "instrument_ids": sorted(instrument_ids),
            })
            return

        # ── publish (called by the pricefeed) ───────────────────────────────────
        if action == "publish":
            instrument_id = str(message.get("instrument_id", "")).strip()
            if not instrument_id:
                await websocket.send_json({"type": "error", "message": "instrument_id is required"})
                return

            try:
                price_value = float(message.get("price"))
            except (TypeError, ValueError):
                await websocket.send_json({"type": "error", "message": "price must be numeric"})
                return

            # Parse previous_close sent by the pricefeed
            previous_close: Optional[float] = None
            raw_pc = message.get("previous_close")
            if raw_pc is not None:
                try:
                    pc = float(raw_pc)
                    if math.isfinite(pc) and pc > 0:
                        previous_close = pc
                except (TypeError, ValueError):
                    pass

            publish_ids = self._expand_publish_ids(instrument_id)
            for publish_id in publish_ids:
                PRICE_CACHE[publish_id] = price_value
                if previous_close is not None:
                    PREV_CLOSE_CACHE[publish_id] = previous_close

                day_change, day_change_pct = _compute_day_change(
                    price_value, PREV_CLOSE_CACHE.get(publish_id)
                )
                if day_change is not None:
                    DAY_CHANGE_CACHE[publish_id]     = day_change
                    DAY_CHANGE_PCT_CACHE[publish_id] = day_change_pct

                await red.set_live_price(
                    publish_id,
                    price_value,
                    previous_close=PREV_CLOSE_CACHE.get(publish_id),
                )
                tick = _build_tick(publish_id, price_value, ts=message.get("ts"), source=message.get("source"))
                await self._broadcast(publish_id, tick)
            return

        await websocket.send_json({"type": "error", "message": "unknown action"})

    async def subscribe_runtime(self, instrument_id: str) -> None:
        instrument_id = str(instrument_id).strip()
        if not instrument_id:
            return
        async with self._lock:
            self._runtime_subscriptions[instrument_id] = (
                self._runtime_subscriptions.get(instrument_id, 0) + 1
            )
        await self._sync_feed_subscriptions()

    async def unsubscribe_runtime(self, instrument_id: str) -> None:
        instrument_id = str(instrument_id).strip()
        if not instrument_id:
            return
        async with self._lock:
            current = self._runtime_subscriptions.get(instrument_id, 0)
            if current <= 1:
                self._runtime_subscriptions.pop(instrument_id, None)
            else:
                self._runtime_subscriptions[instrument_id] = current - 1
        await self._sync_feed_subscriptions()

    async def _broadcast(self, instrument_id: str, tick: dict[str, Any]) -> None:
        async with self._lock:
            recipients = [
                ws
                for ws, instrument_ids in self._subscriptions.items()
                if instrument_id in instrument_ids
            ]
        stale = []
        for ws in recipients:
            try:
                await ws.send_json(tick)
            except Exception:
                stale.append(ws)
        for ws in stale:
            await self.disconnect(ws)

    async def _sync_feed_subscriptions(self) -> None:
        async with self._lock:
            target = set()
            for ws, instrument_ids in self._subscriptions.items():
                if ws in self._feed_connections:
                    continue
                target.update(instrument_ids)
            target.update(self._runtime_subscriptions.keys())
            feed_connections = list(self._feed_connections)
        feed_instrument_ids = sorted({
            self._to_feed_instrument_id(iid)
            for iid in target
            if iid
        })
        payload = {
            "type": "feed_subscription_sync",
            "instrument_ids": feed_instrument_ids,
        }
        stale = []
        for ws in feed_connections:
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            await self.disconnect(ws)

    def _looks_like_upstox_key(self, instrument_id: str) -> bool:
        """Return True if instrument_id is already a valid Upstox key (e.g. NSE_FO|52282)."""
        if "|" not in instrument_id:
            return False
        prefix = instrument_id.split("|", 1)[0]
        return prefix in self._UPSTOX_KEY_PREFIXES

    def _to_feed_instrument_id(self, instrument_id: str) -> str:
        """
        Convert an instrument_id received from a frontend WebSocket subscription
        into the Upstox instrument_key the pricefeed needs.

        Stage 1 — already an Upstox key (contains known segment prefix like NSE_FO|)
                   → return as-is. This covers INDEX_KEYS and upstox_instrument_key
                   values sent directly by the frontend.

        Stage 2 — static XTS_TO_UPSTOX_KEY map built at startup from complete.json.

        Stage 3 — runtime composite-key lookup in UPSTOX_INSTRUMENT_BY_KEY.
                   Handles newly listed strikes whose XTS entry exists in MASTER_DATA
                   but whose mapping was missing from the stale complete.json.
                   On success, the result is cached in XTS_TO_UPSTOX_KEY so stage 2
                   will hit on subsequent calls.

        If all three stages fail: return the raw id with a warning. The pricefeed
        will reject it from Upstox (no prices), but the system keeps running.
        Resolve by calling POST /master-data/reload-upstox.
        """
        instrument_id = str(instrument_id)

        # Stage 1: already a valid Upstox key
        if self._looks_like_upstox_key(instrument_id):
            return instrument_id

        # Stage 2: static map
        mapped = data_utils.get_upstox_instrument_key_by_xts_id(instrument_id)
        if mapped:
            return mapped

        # Stage 3: runtime composite-key lookup
        runtime = data_utils.find_upstox_key_for_xts_id(instrument_id)
        if runtime:
            return runtime

        logger.warning(
            "Cannot resolve Upstox key for instrument_id=%s — "
            "no feed will arrive. Refresh via POST /master-data/reload-upstox.",
            instrument_id,
        )
        return instrument_id

    def _expand_publish_ids(self, instrument_id: str) -> set[str]:
        instrument_id = str(instrument_id)
        expanded = {instrument_id}
        mapped_xts = data_utils.get_xts_instrument_id_by_upstox_key(instrument_id)
        if mapped_xts:
            expanded.add(mapped_xts)
        mapped_upstox = data_utils.get_upstox_instrument_key_by_xts_id(instrument_id)
        if mapped_upstox:
            expanded.add(mapped_upstox)
        return expanded


hub = PriceWebSocketHub()
