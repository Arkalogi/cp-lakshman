import asyncio
import json
import logging
import math

from sqlalchemy import select

from api.commons import enums
from api.config import Config
from api.data import database, models, red, utils
from api.order_routing.service import order_router_worker
from api.prices.ws_hub import hub

logger = logging.getLogger(__name__)


class RMSWorker:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None

    async def run_forever(self) -> None:
        logger.info("RMS worker started.")
        redis_client = red.get_async_redis()
        while True:
            try:
                item = await redis_client.blpop(
                    red.ORDER_SIGNAL_LIST,
                    timeout=Config.RMS_QUEUE_BLOCK_SECONDS,
                )
                if not item:
                    continue
                _, raw_payload = item
                payload = json.loads(raw_payload)
                await self.process_signal(payload)
            except asyncio.CancelledError:
                logger.info("RMS worker stopped.")
                raise
            except Exception:
                logger.exception("RMS worker loop failed")
                await asyncio.sleep(1)

    async def process_signal(self, payload: dict) -> None:
        signal_type = str(payload.get("type") or "").strip().lower()
        signal_id = payload.get("signal_id")
        strategy_id = payload.get("target_id")
        instrument_id = str(payload.get("instrument_id") or "").strip()

        if not signal_type or signal_id is None or strategy_id is None or not instrument_id:
            logger.warning("Skipping malformed signal payload: %s", payload)
            return

        instrument = utils.get_instrument_by_id(instrument_id)
        if not instrument:
            logger.warning("Skipping signal %s: instrument %s not found", signal_id, instrument_id)
            return

        async with database.DbAsyncSession() as db:
            result = await db.execute(
                select(models.StrategySubscription).where(
                    models.StrategySubscription.target_id == strategy_id
                )
            )
            subscriptions = result.scalars().all()

        if not subscriptions:
            logger.info("No subscriptions found for strategy %s", strategy_id)
            return

        if signal_type == enums.SignalType.ENTER_POSITION.value:
            await self._process_entry_signal(payload, subscriptions, instrument)
            return
        if signal_type == enums.SignalType.EXIT_POSITION.value:
            await self._process_exit_signal(payload, subscriptions, instrument)
            return

        logger.warning("Unsupported signal type %s for signal %s", signal_type, signal_id)

    async def _process_entry_signal(self, payload: dict, subscriptions: list, instrument) -> None:
        instrument_id = str(payload["instrument_id"])
        live_price = await self._wait_for_live_price(instrument_id)
        if live_price is None:
            logger.warning(
                "Skipping entry signal %s: live price unavailable for %s",
                payload["signal_id"],
                instrument_id,
            )
            return

        lot_size = max(1, int(instrument.lot_size or 1))
        created_order_ids: list[int] = []
        async with database.DbAsyncSession() as db:
            for subscription in subscriptions:
                existing_order = await self._get_existing_order(
                    db,
                    signal_id=payload["signal_id"],
                    demat_api_id=subscription.subscriber_id,
                )
                if existing_order:
                    continue

                allocated_fund = self._get_allocated_fund(subscription)
                quantity = self._calculate_order_quantity(
                    allocated_fund=allocated_fund,
                    live_price=live_price,
                    lot_size=lot_size,
                )
                if quantity <= 0:
                    logger.info(
                        "Skipping entry signal %s for subscription %s: allocated_fund=%s price=%s lot_size=%s",
                        payload["signal_id"],
                        subscription.id,
                        allocated_fund,
                        live_price,
                        lot_size,
                    )
                    continue

                order = models.Order(
                    tag=self._build_order_tag(payload["signal_id"], subscription.id),
                    instrument_id=instrument_id,
                    trading_symbol=str(payload.get("trading_symbol") or instrument.trading_symbol),
                    side=enums.OrderSide(str(payload["side"]).lower()),
                    quantity=quantity,
                    price=live_price,
                    signal_id=payload["signal_id"],
                    demat_api_id=subscription.subscriber_id,
                    meta_data=json.dumps(
                        {
                            "subscription_id": subscription.id,
                            "strategy_id": subscription.target_id,
                            "allocated_fund": allocated_fund,
                            "entry_signal_id": payload["signal_id"],
                            "source": "rms",
                        },
                        separators=(",", ":"),
                        ensure_ascii=True,
                    ),
                )
                db.add(order)
                await db.flush()
                created_order_ids.append(order.id)
            await db.commit()
        for order_id in created_order_ids:
            await order_router_worker.enqueue_order(order_id)

    async def _process_exit_signal(self, payload: dict, subscriptions: list, instrument) -> None:
        instrument_id = str(payload["instrument_id"])
        live_price = await self._wait_for_live_price(instrument_id)
        if live_price is None:
            logger.warning(
                "Skipping exit signal %s: live price unavailable for %s",
                payload["signal_id"],
                instrument_id,
            )
            return

        entry_signal_id = payload.get("depends_on_signal_id")
        if entry_signal_id is None:
            logger.warning("Skipping exit signal %s: depends_on_signal_id missing", payload["signal_id"])
            return

        created_order_ids: list[int] = []
        async with database.DbAsyncSession() as db:
            for subscription in subscriptions:
                existing_order = await self._get_existing_order(
                    db,
                    signal_id=payload["signal_id"],
                    demat_api_id=subscription.subscriber_id,
                )
                if existing_order:
                    continue

                entry_order = await self._get_existing_order(
                    db,
                    signal_id=entry_signal_id,
                    demat_api_id=subscription.subscriber_id,
                )
                if not entry_order:
                    logger.info(
                        "Skipping exit signal %s for subscription %s: entry order missing",
                        payload["signal_id"],
                        subscription.id,
                    )
                    continue

                entry_quantity = int(entry_order.filled_quantity or entry_order.quantity or 0)
                if entry_quantity <= 0:
                    logger.info(
                        "Skipping exit signal %s for subscription %s: entry quantity unavailable",
                        payload["signal_id"],
                        subscription.id,
                    )
                    continue

                order = models.Order(
                    tag=self._build_order_tag(payload["signal_id"], subscription.id),
                    parent_tag=entry_order.tag,
                    instrument_id=instrument_id,
                    trading_symbol=str(payload.get("trading_symbol") or instrument.trading_symbol),
                    side=enums.OrderSide(str(payload["side"]).lower()),
                    quantity=entry_quantity,
                    price=live_price,
                    signal_id=payload["signal_id"],
                    demat_api_id=subscription.subscriber_id,
                    meta_data=json.dumps(
                        {
                            "subscription_id": subscription.id,
                            "strategy_id": subscription.target_id,
                            "entry_signal_id": entry_signal_id,
                            "entry_order_id": entry_order.id,
                            "source": "rms",
                        },
                        separators=(",", ":"),
                        ensure_ascii=True,
                    ),
                )
                db.add(order)
                await db.flush()
                created_order_ids.append(order.id)
            await db.commit()
        for order_id in created_order_ids:
            await order_router_worker.enqueue_order(order_id)

    async def _wait_for_live_price(self, instrument_id: str) -> float | None:
        await hub.subscribe_runtime(instrument_id)
        try:
            deadline = asyncio.get_running_loop().time() + Config.RMS_PRICE_WAIT_SECONDS
            while True:
                live_price = await utils.get_current_price(instrument_id)
                if live_price is not None and math.isfinite(float(live_price)) and float(live_price) > 0:
                    return float(live_price)
                if asyncio.get_running_loop().time() >= deadline:
                    return None
                await asyncio.sleep(Config.RMS_PRICE_POLL_SECONDS)
        finally:
            await hub.unsubscribe_runtime(instrument_id)

    @staticmethod
    async def _get_existing_order(db, *, signal_id: int, demat_api_id: int):
        result = await db.execute(
            select(models.Order).where(
                models.Order.signal_id == signal_id,
                models.Order.demat_api_id == demat_api_id,
            )
        )
        return result.scalars().first()

    @staticmethod
    def _build_order_tag(signal_id: int, subscription_id: int) -> str:
        return f"sig-{signal_id}-sub-{subscription_id}"

    @staticmethod
    def _calculate_order_quantity(
        *,
        allocated_fund: float,
        live_price: float,
        lot_size: int,
    ) -> int:
        if allocated_fund <= 0 or live_price <= 0 or lot_size <= 0:
            return 0
        lots = math.floor(allocated_fund / (live_price * lot_size))
        return max(0, lots * lot_size)

    @staticmethod
    def _get_allocated_fund(subscription) -> float:
        fund_deployed = float(subscription.fund_deployed or 0)
        if fund_deployed > 0:
            return fund_deployed

        total_fund = float(subscription.total_fund or 0)
        allocation = float(subscription.fund_allocation_precentage or 0)
        if allocation > 1:
            allocation /= 100.0
        return max(0.0, total_fund * allocation)


rms_worker = RMSWorker()
