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
            instrument = utils.get_instrument_by_id(instrument_id)
            lot_size = 0
            if instrument and instrument.lot_size:
                try:
                    lot_size = int(instrument.lot_size)
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
                    if current_price is None:
                        order = models.Order(
                            tag=f"signal:{signal_id}:{demat_api_subscription.subscriber_id}",
                            instrument_id=instrument_id,
                            trading_symbol=order_signal.get("trading_symbol")
                            or (instrument.trading_symbol if instrument else ""),
                            side=enums.OrderSide(
                                order_signal.get("side") or enums.OrderSide.BUY.value
                            ),
                            quantity=0,
                            price=0,
                            status=enums.OrderStatus.FAILED.value,
                            filled_quantity=0,
                            average_price=0,
                            parent_tag=f"signal:{signal_id}" if signal_id is not None else None,
                            signal_id=signal_id,
                            api_id=demat_api_subscription.subscriber_id,
                            error_message="Price not available for allocation.",
                            meta_data=json.dumps(
                                {"signal": order_signal},
                                separators=(",", ":"),
                                ensure_ascii=True,
                            ),
                        )
                        db.add(order)
                        logger.warning(
                            "Created rejected order for signal %s due to missing price data.",
                            signal_id,
                        )
                        continue

                    total_fund = demat_api_subscription.total_fund or 0
                    fund_allocation_percentage = demat_api_subscription.fund_allocation_precentage or 0
                    allocated_fund = total_fund * fund_allocation_percentage / 100
                    if allocated_fund <= 0:
                        logger.warning(
                            "Allocated fund is zero for subscriber %s on signal %s. Skipping.",
                            demat_api_subscription.subscriber_id,
                            signal_id,
                        )
                        order = models.Order(
                            tag=f"signal:{signal_id}:{demat_api_subscription.subscriber_id}",
                            instrument_id=instrument_id,
                            trading_symbol=order_signal.get("trading_symbol")
                            or (instrument.trading_symbol if instrument else ""),
                            side=enums.OrderSide(
                                order_signal.get("side") or enums.OrderSide.BUY.value
                            ),
                            quantity=0,
                            price=current_price or 0,
                            status=enums.OrderStatus.FAILED.value,
                            filled_quantity=0,
                            average_price=0,
                            parent_tag=f"signal:{signal_id}" if signal_id is not None else None,
                            signal_id=signal_id,
                            api_id=demat_api_subscription.subscriber_id,
                            error_message="Insufficient allocated funds.",
                            meta_data=json.dumps(
                                {"signal": order_signal},
                                separators=(",", ":"),
                                ensure_ascii=True,
                            ),
                        )
                        db.add(order)
                        continue

                    quantity = int(allocated_fund / current_price)
                    if lot_size > 0:
                        quantity = (quantity // lot_size) * lot_size

                    if quantity <= 0:
                        logger.warning(
                            "Allocated quantity is zero for signal %s. Skipping.",
                            signal_id,
                        )
                        order = models.Order(
                            tag=f"signal:{signal_id}:{demat_api_subscription.subscriber_id}",
                            instrument_id=instrument_id,
                            trading_symbol=order_signal.get("trading_symbol")
                            or (instrument.trading_symbol if instrument else ""),
                            side=enums.OrderSide(
                                order_signal.get("side") or enums.OrderSide.BUY.value
                            ),
                            quantity=0,
                            price=current_price,
                            status=enums.OrderStatus.FAILED.value,
                            filled_quantity=0,
                            average_price=0,
                            parent_tag=f"signal:{signal_id}" if signal_id is not None else None,
                            signal_id=signal_id,
                            api_id=demat_api_subscription.subscriber_id,
                            error_message="Allocated quantity less than 1.",
                            meta_data=json.dumps(
                                {"signal": order_signal},
                                separators=(",", ":"),
                                ensure_ascii=True,
                            ),
                        )
                        db.add(order)
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

                    order = models.Order(
                        tag=f"signal:{signal_id}:{demat_api_subscription.subscriber_id}",
                        instrument_id=instrument_id,
                        trading_symbol=instrument.trading_symbol,
                        side=enums.OrderSide(
                            order_signal.get("side") or enums.OrderSide.BUY.value
                        ),
                        quantity=quantity,
                        price=current_price,
                        status=enums.OrderStatus.PENDING.value,
                        filled_quantity=0,
                        average_price=0,
                        signal_id=signal_id,
                        demat_api_id=demat_api_subscription.subscriber_id,
                        meta_data=json.dumps(
                            {"signal": order_signal, "routed": routed_signal},
                            separators=(",", ":"),
                            ensure_ascii=True,
                        ),
                    )
                    db.add(order)
                await db.commit()
        except Exception:
            logger.exception("Allocator failed to process order signal.")
