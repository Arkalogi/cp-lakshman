import asyncio
import json
import logging
from typing import Dict, List
from sqlalchemy import select
from api.commons import enums
from api.data import database, models, red, utils


logger = logging.getLogger(__name__)


async def thread_spawn_loop():
    logger.info("Allocator loop started")
    redis_client = red.get_async_redis()
    while True:
        signal = await redis_client.blpop(red.ORDER_SIGNAL_LIST, timeout=1)
        if not signal:
            continue
        try:
            order_signal = json.loads(signal[1])
            signal_target_id = order_signal.get("target_id")
            signal_id = order_signal.get("signal_id")
            instrument_id = order_signal.get("instrument_id")
            if signal_target_id is None or instrument_id is None:
                logger.warning("Skipping invalid order signal payload: %s", order_signal)
                continue

            current_price = await utils.get_current_price(instrument_id)
            if current_price is None:
                logger.warning(
                    "Skipping order allocation for signal %s due to missing price data.",
                    signal_id,
                )
                continue

            instrument = utils.get_instrument_by_id(instrument_id)
            lot_size = 0
            if instrument and instrument.lot_size:
                try:
                    lot_size = instrument.lot_size
                except (TypeError, ValueError):
                    logger.warning(
                        "Invalid lot size %s for instrument %s.",
                        instrument.lot_size,
                        instrument_id,
                    )

            parent_order = None
            if order_signal.get("depends_on_signal_id"):
                async with database.DbAsyncSession() as db:
                    result = await db.execute(
                        select(models.Order).where(
                            models.Order.signal_id
                            == order_signal["depends_on_signal_id"]
                        )
                    )
                    parent_order = result.scalars().one_or_none()

            async with database.DbAsyncSession() as db:
                result = await db.execute(
                    select(models.StrategySubscription)
                    .where(models.StrategySubscription.target_id == signal_target_id)
                )
                demat_api_subscriptions = result.scalars().all()

                for demat_api_subscription in demat_api_subscriptions:
                    total_fund = demat_api_subscription.total_fund or 0
                    fund_allocation_percentage = demat_api_subscription.fund_allocation_precentage or 0
                    allocated_fund = total_fund * fund_allocation_percentage / 100
                    if allocated_fund <= 0:
                        logger.warning(
                            "Allocated fund is zero for subscriber %s on signal %s. Skipping.",
                            demat_api_subscription.subscriber_id,
                            signal_id,
                        )
                        continue

                    quantity = int(allocated_fund / current_price)
                    if lot_size > 0:
                        quantity = (quantity // lot_size) * lot_size

                    if quantity <= 0:
                        logger.warning(
                            "Allocated quantity is zero for signal %s. Skipping.",
                            signal_id,
                        )
                        continue

                    if parent_order:
                        filled_quantity = parent_order.filled_quantity or 0
                        if filled_quantity < quantity:
                            quantity = filled_quantity
                        if quantity <= 0:
                            logger.warning(
                                "Exit signal quantity is zero for signal %s. Skipping.",
                                signal_id,
                            )
                            continue
                    
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
        except Exception:
            logger.exception("Allocator failed to process order signal.")
