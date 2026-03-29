import asyncio
import json
import logging

from sqlalchemy import select

from api.commons import enums
from api.data import database, models, red
from api.order_routing.adapters import (
    BrokerAdapter,
    DemoBrokerAdapter,
    GrowBrokerAdapter,
    UpstoxBrokerAdapter,
    ZerodhaBrokerAdapter,
)

logger = logging.getLogger(__name__)


class OrderRouterWorker:
    def __init__(self) -> None:
        self._adapters = {
            enums.DematProvider.UPSTOX.value: UpstoxBrokerAdapter(),
            enums.DematProvider.ZERODHA.value: ZerodhaBrokerAdapter(),
            enums.DematProvider.GROW.value: GrowBrokerAdapter(),
            enums.DematProvider.DEMO.value: DemoBrokerAdapter(),
            enums.DematProvider.ARKALOGI.value: DemoBrokerAdapter(),
        }

    async def run_forever(self) -> None:
        logger.info("Order router worker started.")
        redis_client = red.get_async_redis()
        while True:
            try:
                item = await redis_client.blpop(red.ORDER_ROUTER_LIST, timeout=5)
                if item:
                    _, raw_payload = item
                    payload = json.loads(raw_payload)
                    await self.route_order_id(int(payload["order_id"]))
                    continue
                await self.route_pending_orders()
            except asyncio.CancelledError:
                logger.info("Order router worker stopped.")
                raise
            except Exception:
                logger.exception("Order router worker loop failed")
                await asyncio.sleep(1)

    async def route_pending_orders(self) -> None:
        async with database.DbAsyncSession() as db:
            result = await db.execute(
                select(models.Order.id).where(
                    models.Order.status == enums.OrderStatus.PENDING.value,
                    models.Order.broker_order_id.is_(None),
                )
            )
            order_ids = result.scalars().all()
        for order_id in order_ids:
            await self.route_order_id(int(order_id))

    async def enqueue_order(self, order_id: int) -> None:
        payload = json.dumps({"order_id": int(order_id)}, separators=(",", ":"), ensure_ascii=True)
        await red.get_async_redis().rpush(red.ORDER_ROUTER_LIST, payload)

    async def route_order_id(self, order_id: int) -> None:
        async with database.DbAsyncSession() as db:
            result = await db.execute(
                select(models.Order, models.DematApi)
                .join(models.DematApi, models.Order.demat_api_id == models.DematApi.id)
                .where(models.Order.id == order_id)
            )
            row = result.one_or_none()
            if not row:
                logger.warning("Order %s not found for routing", order_id)
                return

            order, demat_api = row
            if order.broker_order_id:
                return

            try:
                adapter = self._resolve_adapter(demat_api)
                result = await adapter.place_order(order, demat_api)
                order.broker_order_id = result.broker_order_id
                order.status = result.status
                order.filled_quantity = result.filled_quantity
                order.average_price = result.average_price
                order.error_code = result.error_code
                order.error_message = result.error_message
            except Exception as exc:
                logger.exception("Failed to route order %s", order_id)
                order.status = enums.OrderStatus.FAILED.value
                order.error_code = "ROUTE"
                order.error_message = str(exc)

            db.add(order)
            await db.commit()

    def _resolve_adapter(self, demat_api: models.DematApi) -> BrokerAdapter:
        config = demat_api.config or {}
        demat_provider = str(
            config.get("demat_provider") or config.get("provider") or enums.DematProvider.DEMO.value
        ).strip().lower()
        adapter = self._adapters.get(demat_provider)
        if not adapter:
            raise ValueError(f"Unsupported demat provider: {demat_provider}")
        return adapter


order_router_worker = OrderRouterWorker()
