from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from api.commons import enums
from api.data import database, models, red, utils
from api.data.local import MASTER_DATA, TOKEN_MAP
from api.data.utils import load_master_data

logger = logging.getLogger(__name__)


@dataclass
class Rule:
    name: str
    when: dict[str, Any]
    action: str = "block"


def load_rules(path: str) -> list[Rule]:
    if not os.path.exists(path):
        logger.warning("Rules file not found at %s. Continuing without rules.", path)
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Rule(**r) for r in raw]


def eval_rules(rules: list[Rule], symbol: str, target_qty: int) -> tuple[bool, str | None]:
    for rule in rules:
        when = rule.when or {}
        if "max_qty" in when and target_qty > float(when["max_qty"]):
            return True, f"Blocked by rule {rule.name}: max_qty"
        if "symbol_in" in when and symbol in set(when["symbol_in"]):
            return True, f"Blocked by rule {rule.name}: symbol_in"
    return False, None


def _new_failed_order(
    *,
    signal_id: Any,
    subscriber_id: Any,
    instrument_id: Any,
    trading_symbol: str,
    side_enum: enums.OrderSide,
    price: float,
    order_signal: dict[str, Any],
    error_message: str,
) -> models.Order:
    return models.Order(
        tag=f"signal:{signal_id}:{subscriber_id}",
        instrument_id=instrument_id,
        trading_symbol=trading_symbol,
        side=side_enum,
        quantity=0,
        price=price,
        status=enums.OrderStatus.FAILED.value,
        filled_quantity=0,
        average_price=0,
        signal_id=signal_id,
        demat_api_id=subscriber_id,
        error_message=error_message,
        meta_data=json.dumps(
            {"signal": order_signal},
            separators=(",", ":"),
            ensure_ascii=True,
        ),
    )


async def run():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info("Loading master data")
    await load_master_data()
    _ = MASTER_DATA, TOKEN_MAP

    rules_path = os.getenv("ALLOCATOR_RULES_PATH", "configs/allocator_rules.json")
    rules = load_rules(rules_path)
    logger.info("Allocator started with %d rule(s)", len(rules))

    redis_client = red.get_async_redis()
    while True:
        signal = await redis_client.blpop(red.ORDER_SIGNAL_LIST, timeout=1)
        if not signal:
            continue
        try:
            raw_payload = signal[1]
            order_signal = json.loads(raw_payload)
            signal_target_id = order_signal.get("target_id")
            signal_id = order_signal.get("signal_id")
            instrument_id = order_signal.get("instrument_id")
            side_value = order_signal.get("side")
            side_enum = (
                enums.OrderSide(side_value)
                if side_value in enums.OrderSide._value2member_map_
                else enums.OrderSide.BUY
            )
            if signal_target_id is None or instrument_id is None:
                logger.warning("Skipping invalid order signal payload: %s", order_signal)
                continue

            current_price = await utils.get_current_price(instrument_id)
            instrument = utils.get_instrument_by_id(instrument_id)
            trading_symbol = order_signal.get("trading_symbol") or (
                instrument.trading_symbol if instrument else ""
            )
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

            checkpoint_key = f"signal:{signal_id}"
            async with database.DbAsyncSession() as db:
                checkpoint = await db.execute(
                    select(models.WorkerCheckpoint).where(
                        models.WorkerCheckpoint.worker_name == "allocator",
                        models.WorkerCheckpoint.event_key == checkpoint_key,
                    )
                )
                if checkpoint.scalars().one_or_none():
                    logger.info("Skipping already processed signal %s", signal_id)
                    continue

                result = await db.execute(
                    select(models.StrategySubscription)
                    .where(models.StrategySubscription.target_id == signal_target_id)
                )
                demat_api_subscriptions = result.scalars().all()

                for demat_api_subscription in demat_api_subscriptions:
                    parent_order = None
                    subscriber_id = demat_api_subscription.subscriber_id
                    existing_order = await db.execute(
                        select(models.Order).where(
                            models.Order.signal_id == signal_id,
                            models.Order.demat_api_id == subscriber_id,
                        )
                    )
                    if existing_order.scalars().one_or_none():
                        logger.info(
                            "Order already exists for signal %s and subscriber %s, skipping.",
                            signal_id,
                            subscriber_id,
                        )
                        continue

                    if order_signal.get("depends_on_signal_id"):
                        result = await db.execute(
                            select(models.Order).where(
                                models.Order.signal_id
                                == order_signal["depends_on_signal_id"],
                                models.Order.demat_api_id == subscriber_id,
                            )
                        )
                        parent_order = result.scalars().one_or_none()
                        if parent_order and parent_order.side == enums.OrderSide.BUY:
                            side_enum = enums.OrderSide.SELL
                        elif parent_order and parent_order.side == enums.OrderSide.SELL:
                            side_enum = enums.OrderSide.BUY

                    if current_price is None:
                        db.add(
                            _new_failed_order(
                                signal_id=signal_id,
                                subscriber_id=subscriber_id,
                                instrument_id=instrument_id,
                                trading_symbol=trading_symbol,
                                side_enum=side_enum,
                                price=0,
                                order_signal=order_signal,
                                error_message="Price not available for allocation.",
                            )
                        )
                        continue

                    total_fund = demat_api_subscription.total_fund or 0
                    fund_allocation_percentage = (
                        demat_api_subscription.fund_allocation_precentage or 0
                    )
                    allocated_fund = total_fund * fund_allocation_percentage / 100
                    if allocated_fund <= 0:
                        db.add(
                            _new_failed_order(
                                signal_id=signal_id,
                                subscriber_id=subscriber_id,
                                instrument_id=instrument_id,
                                trading_symbol=trading_symbol,
                                side_enum=side_enum,
                                price=current_price or 0,
                                order_signal=order_signal,
                                error_message="Insufficient allocated funds.",
                            )
                        )
                        continue

                    quantity = int(allocated_fund / current_price)
                    if lot_size > 0:
                        quantity = (quantity // lot_size) * lot_size

                    if parent_order:
                        filled_quantity = parent_order.filled_quantity or 0
                        if filled_quantity <= 0:
                            db.add(
                                _new_failed_order(
                                    signal_id=signal_id,
                                    subscriber_id=subscriber_id,
                                    instrument_id=instrument_id,
                                    trading_symbol=trading_symbol,
                                    side_enum=side_enum,
                                    price=current_price,
                                    order_signal=order_signal,
                                    error_message="Parent order filled quantity is zero.",
                                )
                            )
                            continue
                        quantity = min(quantity, filled_quantity)

                    if quantity <= 0:
                        db.add(
                            _new_failed_order(
                                signal_id=signal_id,
                                subscriber_id=subscriber_id,
                                instrument_id=instrument_id,
                                trading_symbol=trading_symbol,
                                side_enum=side_enum,
                                price=current_price,
                                order_signal=order_signal,
                                error_message="Allocated quantity less than 1.",
                            )
                        )
                        continue

                    blocked, reason = eval_rules(rules, trading_symbol, quantity)
                    if blocked:
                        logger.info(
                            "Blocked signal %s for subscriber %s: %s",
                            signal_id,
                            subscriber_id,
                            reason,
                        )
                        db.add(
                            _new_failed_order(
                                signal_id=signal_id,
                                subscriber_id=subscriber_id,
                                instrument_id=instrument_id,
                                trading_symbol=trading_symbol,
                                side_enum=side_enum,
                                price=current_price,
                                order_signal=order_signal,
                                error_message=reason or "Blocked by allocation rule.",
                            )
                        )
                        continue

                    routed_signal = {
                        **order_signal,
                        "subscriber_id": subscriber_id,
                        "quantity": quantity,
                    }
                    await redis_client.rpush(
                        red.ORDER_ROUTER_LIST,
                        json.dumps(
                            routed_signal, separators=(",", ":"), ensure_ascii=True
                        ),
                    )
                    order = models.Order(
                        tag=f"signal:{signal_id}:{subscriber_id}",
                        instrument_id=instrument_id,
                        trading_symbol=trading_symbol,
                        side=side_enum,
                        quantity=quantity,
                        price=current_price,
                        status=enums.OrderStatus.PENDING.value,
                        filled_quantity=0,
                        average_price=0,
                        signal_id=signal_id,
                        demat_api_id=subscriber_id,
                        meta_data=json.dumps(
                            {"signal": order_signal, "routed": routed_signal},
                            separators=(",", ":"),
                            ensure_ascii=True,
                        ),
                    )
                    db.add(order)
                db.add(
                    models.WorkerCheckpoint(
                        worker_name="allocator",
                        event_key=checkpoint_key,
                        payload=raw_payload.decode("utf-8", errors="replace")
                        if isinstance(raw_payload, (bytes, bytearray))
                        else str(raw_payload),
                    )
                )
                await db.commit()
        except Exception:
            logger.exception("Allocator failed to process order signal.")
