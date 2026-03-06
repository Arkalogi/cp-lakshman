import asyncio
from typing import Any

from fastapi import WebSocket

from api.data.local import PRICE_CACHE
from api.data import utils as data_utils


class PriceWebSocketHub:
    def __init__(self) -> None:
        self._subscriptions: dict[WebSocket, set[str]] = {}
        self._feed_connections: set[WebSocket] = set()
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
        if action == "register_feed":
            async with self._lock:
                self._feed_connections.add(websocket)
            await websocket.send_json({"type": "ack", "action": "register_feed"})
            await self._sync_feed_subscriptions()
            return

        if action == "subscribe":
            instrument_ids = {
                str(instrument_id)
                for instrument_id in (message.get("instrument_ids") or [])
                if instrument_id is not None
            }
            async with self._lock:
                current = self._subscriptions.get(websocket, set())
                current.update(instrument_ids)
                self._subscriptions[websocket] = current
            await self._sync_feed_subscriptions()

            # Send snapshot for already available prices.
            for instrument_id in instrument_ids:
                if instrument_id in PRICE_CACHE:
                    await websocket.send_json(
                        {
                            "type": "price",
                            "instrument_id": instrument_id,
                            "price": PRICE_CACHE[instrument_id],
                            "source": "cache",
                        }
                    )
            await websocket.send_json(
                {
                    "type": "ack",
                    "action": "subscribe",
                    "instrument_ids": sorted(instrument_ids),
                }
            )
            return

        if action == "unsubscribe":
            instrument_ids = {
                str(instrument_id)
                for instrument_id in (message.get("instrument_ids") or [])
                if instrument_id is not None
            }
            async with self._lock:
                current = self._subscriptions.get(websocket, set())
                current.difference_update(instrument_ids)
                self._subscriptions[websocket] = current
            await self._sync_feed_subscriptions()
            await websocket.send_json(
                {
                    "type": "ack",
                    "action": "unsubscribe",
                    "instrument_ids": sorted(instrument_ids),
                }
            )
            return

        if action == "publish":
            instrument_id = str(message.get("instrument_id", "")).strip()
            price = message.get("price")
            if not instrument_id:
                await websocket.send_json(
                    {"type": "error", "message": "instrument_id is required"}
                )
                return
            try:
                price_value = float(price)
            except (TypeError, ValueError):
                await websocket.send_json(
                    {"type": "error", "message": "price must be numeric"}
                )
                return

            publish_ids = self._expand_publish_ids(instrument_id)
            for publish_id in publish_ids:
                PRICE_CACHE[publish_id] = price_value
                tick = {
                    "type": "price",
                    "instrument_id": publish_id,
                    "price": price_value,
                    "ts": message.get("ts"),
                    "source": message.get("source"),
                }
                await self._broadcast(publish_id, tick)
            return

        await websocket.send_json({"type": "error", "message": "unknown action"})

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
            feed_connections = list(self._feed_connections)
        feed_instrument_ids = sorted(
            {
                self._to_feed_instrument_id(instrument_id)
                for instrument_id in target
                if instrument_id
            }
        )
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

    def _to_feed_instrument_id(self, instrument_id: str) -> str:
        mapped = data_utils.get_upstox_instrument_key_by_xts_id(str(instrument_id))
        return mapped or str(instrument_id)

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
