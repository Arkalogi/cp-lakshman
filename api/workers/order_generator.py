import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from api.commons import enums
from api.data import database, models
from api.demat_apis import upstox

_running_target_ids = set()


def _normalize_provider_value(provider):
    if isinstance(provider, enums.ApiProvider):
        return provider.value
    return provider


async def thread_spawn_loop():
    while True:
        async with database.DbAsyncSession() as db:
            result = await db.execute(
                select(models.DematApiSubscription).options(
                    selectinload(models.DematApiSubscription.target)
                )
            )
            demat_api_subscriptions = result.scalars().all()
            for demat_api_subscription in demat_api_subscriptions:
                target = demat_api_subscription.target
                if not target or not target.config:
                    continue

                target_api_config = target.config
                provider_value = _normalize_provider_value(
                    target_api_config.get("api_provider")
                )
                if provider_value != enums.ApiProvider.UPSTOX.value:
                    continue

                if target.id in _running_target_ids:
                    continue

                task = asyncio.create_task(upstox.start(target_api_config))
                _running_target_ids.add(target.id)
                task.add_done_callback(lambda _, target_id=target.id: _running_target_ids.discard(target_id))
        await asyncio.sleep(1)
