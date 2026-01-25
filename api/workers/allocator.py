import asyncio
import json
import logging
from typing import Dict, List
from sqlalchemy import select
from api.data import database, models, red


logger = logging.getLogger(__name__)

demat_api_subscriptions: Dict[int, List[models.DematApiSubscription]] = {}


async def thread_spawn_loop():
    logger.info("Order generator loop started")
    redis_client = red.get_async_redis()
    while True:
        signal = await redis_client.blpop(red.ORDER_SIGNAL_LIST, timeout=1)
        if not signal:
            continue
        order_signal = json.loads(signal[1])
        signal_target_id = order_signal["target_id"]
        base_quantity = order_signal["quantity"]
        async with database.DbAsyncSession() as db:
            result = await db.execute(
                select(models.DematApiSubscription)
                .where(models.DematApiSubscription.is_active == True)
                .where(models.DematApiSubscription.target_id == signal_target_id)
            )
            demat_api_subscriptions = result.scalars().all()

        for demat_api_subscription in demat_api_subscriptions:
            quantity = base_quantity * demat_api_subscription.multiplier
            routed_signal = {
                **order_signal,
                "subscriber_id": demat_api_subscription.subscriber_id,
                "quantity": quantity,
            }
            await redis_client.rpush(
                red.ORDER_ROUTER_LIST,
                json.dumps(routed_signal, separators=(",", ":"), ensure_ascii=True),
            )