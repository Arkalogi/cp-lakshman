import asyncio
import json
import logging
from typing import Dict, List
from sqlalchemy import select
from api.data import database, models, red


logger = logging.getLogger(__name__)

demat_api_subscriptions: Dict[int, List[models.DematApiSubscription]] = {}


async def thread_spawn_loop():
    logger.info("Allocator loop started")
    redis_client = red.get_async_redis()
    while True:
        signal = await redis_client.blpop(red.ORDER_SIGNAL_LIST, timeout=1)
        if not signal:
            continue
        try:
            order_signal = json.loads(signal[1])
            signal_target_id = order_signal["target_id"]
            base_quantity = int(float(order_signal.get("quantity") or 0))
            parent_tag = order_signal.get("order_id")
            parent_order = None
            async with database.DbAsyncSession() as db:
                result = await db.execute(
                    select(models.DematApiSubscription)
                    .where(models.DematApiSubscription.is_active == True)
                    .where(models.DematApiSubscription.target_id == signal_target_id)
                )
                demat_api_subscriptions = result.scalars().all()
                if parent_tag:
                    parent_result = await db.execute(
                        select(models.Order).where(models.Order.tag == parent_tag)
                    )
                    parent_order = parent_result.scalars().one_or_none()

                for demat_api_subscription in demat_api_subscriptions:
                    quantity = base_quantity * demat_api_subscription.multiplier
                    routed_signal = {
                        **order_signal,
                        "subscriber_id": demat_api_subscription.subscriber_id,
                        "quantity": quantity,
                    }
                    await redis_client.rpush(
                        red.ORDER_ROUTER_LIST,
                        json.dumps(
                            routed_signal, separators=(",", ":"), ensure_ascii=True
                        ),
                    )
                await db.commit()
        except Exception:
            logger.exception("Allocator failed to process order signal.")
