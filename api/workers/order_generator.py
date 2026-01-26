import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from api.commons import enums
from api.data import database, models
from api.demat_apis.upstox import UpstoxApi

_running_target_ids = set()
logger = logging.getLogger(__name__)


def _normalize_provider_value(provider):
    if isinstance(provider, enums.ApiProvider):
        return provider.value
    return provider


async def thread_spawn_loop():
    logger.info("Order generator loop started")
    while True:
        try:
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

                    logger.info("Starting order updates for target_id=%s", target.id)
                    upstox_api = UpstoxApi(
                        api_id=target.id,
                        api_key=target_api_config.get("api_key"),
                        api_secret=target_api_config.get("api_secret"),
                        redirect_url=target_api_config.get("redirect_url"),
                        mobile_number=target_api_config.get("mobile_number"),
                        totp_secret=target_api_config.get("totp_secret"),
                        pin=target_api_config.get("pin"),
                    )
                    livefeed_token, livefeed_refresh_token, access_token = upstox_api.login()
                    task = asyncio.create_task(
                        upstox_api.start_order_update_socket(access_token)
                    )

                    _running_target_ids.add(target.id)
                    task.add_done_callback(
                        lambda _, target_id=target.id: _running_target_ids.discard(
                            target_id
                        )
                    )
        except Exception:
            logger.exception("Order generator loop error")
        await asyncio.sleep(1)
