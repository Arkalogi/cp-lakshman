import json
import logging

from sqlalchemy import select

from api.commons import enums
from api.data import database, models, red
from api.demat_apis.brokers import build_broker_client

logger = logging.getLogger(__name__)


def _map_broker_status(status: str) -> str:
    status_value = (status or "").strip().lower()
    if status_value in {"complete", "completed", "filled"}:
        return enums.OrderStatus.COMPLETED.value
    if status_value in {"rejected", "cancelled", "canceled", "failed"}:
        return enums.OrderStatus.FAILED.value
    return enums.OrderStatus.PENDING.value


async def thread_spawn_loop():
    logger.info("Order router loop started")
    redis_client = red.get_async_redis()
    while True:
        payload = await redis_client.blpop(red.ORDER_ROUTER_LIST, timeout=1)
        if not payload:
            continue
        try:
            raw_payload = payload[1]
            routed_signal = json.loads(raw_payload)
            subscriber_id = routed_signal.get("subscriber_id")
            signal_id = routed_signal.get("signal_id")
            if subscriber_id is None or signal_id is None:
                logger.warning("Skipping invalid routed signal payload: %s", routed_signal)
                continue

            checkpoint_key = f"signal:{signal_id}:subscriber:{subscriber_id}"
            async with database.DbAsyncSession() as db:
                checkpoint = await db.execute(
                    select(models.WorkerCheckpoint).where(
                        models.WorkerCheckpoint.worker_name == "order_router",
                        models.WorkerCheckpoint.event_key == checkpoint_key,
                    )
                )
                if checkpoint.scalars().one_or_none():
                    logger.info(
                        "Skipping already routed signal %s for subscriber %s",
                        signal_id,
                        subscriber_id,
                    )
                    continue

                result = await db.execute(
                    select(models.DematApi).where(models.DematApi.id == subscriber_id)
                )
                demat_api = result.scalars().one_or_none()
                if not demat_api:
                    logger.warning("DematApi %s not found for routed signal %s", subscriber_id, signal_id)
                    continue

                broker = build_broker_client(demat_api)
                broker_result = await broker.place_order(routed_signal)
                broker_status = None

                result = await db.execute(
                    select(models.Order).where(
                        models.Order.demat_api_id == subscriber_id,
                        models.Order.signal_id == signal_id,
                    )
                )
                order = result.scalars().one_or_none()
                if not order:
                    logger.warning("Order not found for routed signal %s", routed_signal)
                    continue

                status = broker_result.get("status")
                if status == "success":
                    order.status = enums.OrderStatus.PENDING.value
                    order.broker_order_id = broker_result.get("order_id")
                else:
                    order.status = enums.OrderStatus.FAILED.value
                    order.error_message = broker_result.get("message") or "Broker rejected order"

                if order.status == enums.OrderStatus.PENDING.value and order.broker_order_id:
                    broker_status = await broker.get_order_status(order.broker_order_id)
                    if broker_status.get("status") != "error":
                        order.status = _map_broker_status(broker_status.get("status"))
                        if broker_status.get("filled_quantity") is not None:
                            order.filled_quantity = broker_status.get("filled_quantity")
                        if broker_status.get("average_price") is not None:
                            order.average_price = broker_status.get("average_price")

                order.meta_data = json.dumps(
                    {
                        "routed": routed_signal,
                        "broker_result": broker_result,
                        "broker_status": broker_status if order.broker_order_id else None,
                    },
                    separators=(",", ":"),
                    ensure_ascii=True,
                )
                db.add(
                    models.WorkerCheckpoint(
                        worker_name="order_router",
                        event_key=checkpoint_key,
                        payload=raw_payload.decode("utf-8", errors="replace")
                        if isinstance(raw_payload, (bytes, bytearray))
                        else str(raw_payload),
                    )
                )
                db.add(order)
                await db.commit()
                await db.refresh(order)
        except Exception:
            logger.exception("Order router failed to process routed signal.")
