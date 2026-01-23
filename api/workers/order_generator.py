import asyncio
from sqlalchemy import select
from api.commons import enums
from api.data import database, models
from api.demat_apis import upstox


async def thread_spawn_loop():
    while True:
        async with database.DbAsyncSession() as db:
            result = await db.execute(select(models.DematApiSubscription))
            demat_api_subscriptions = result.scalars().all()
            for demat_api_subscription in demat_api_subscriptions:
                target_api_config = demat_api_subscription.target.config
                if target_api_config["api_provider"] == enums.ApiProvider.UPSTOX:
                    asyncio.create_task(upstox.start(target_api_config))
                demat_api_subscription.subscriber
        await asyncio.sleep(1)
