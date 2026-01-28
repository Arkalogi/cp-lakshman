import json
import logging
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.commons import enums
from api.commons.schemas import ResponseSchema
from api.commons.utils import model_list_to_dict, model_to_dict
from api.data import database, models
from api.demat_apis.paper import PaperAPI
from api.signals.schemas import SignalCreateSchema

logger = logging.getLogger(__name__)


def _normalize_provider_value(provider):
    if isinstance(provider, enums.ApiProvider):
        return provider.value
    return provider


async def add_signal_data(signal_data: SignalCreateSchema):
    async with database.DbAsyncSession() as db:
        signal = models.Signal(
            strategy_id=signal_data.strategy_id,
            instrument_id=signal_data.instrument_id,
            trading_symbol=signal_data.trading_symbol,
            side=signal_data.side,
            quantity=signal_data.quantity,
            price=signal_data.price,
            meta_data=signal_data.meta_data,
        )
        db.add(signal)
        await db.commit()
        await db.refresh(signal)

        result = await db.execute(
            select(models.StrategySubscription)
            .options(selectinload(models.StrategySubscription.subscriber))
            .where(models.StrategySubscription.target_id == signal.strategy_id)
        )
        subscriptions = result.scalars().all()

        placed_orders: List[Dict[str, str]] = []
        for subscription in subscriptions:
            subscriber = subscription.subscriber
            if not subscriber:
                continue
            config = subscriber.config or {}
            provider_value = _normalize_provider_value(config.get("api_provider"))
            if provider_value not in {enums.ApiProvider.PAPER.value, None}:
                logger.warning(
                    "Skipping subscriber_id=%s due to unsupported provider=%s",
                    subscriber.id,
                    provider_value,
                )
                continue

            multiplier = subscription.multiplier or 1
            quantity = int(signal.quantity) * multiplier
            if quantity <= 0:
                continue

            order_details = {
                "instrument_id": signal.instrument_id,
                "trading_symbol": signal.trading_symbol,
                "side": signal.side.value,
                "quantity": quantity,
                "price": signal.price,
            }

            paper_api = PaperAPI(
                api_id=str(subscriber.id),
                api_key=str(config.get("api_key") or ""),
                api_secret=str(config.get("api_secret") or ""),
            )
            await paper_api.login()
            response = await paper_api.place_order(order_details)

            success = response.get("status") == "success"
            broker_order_id = response.get("order_id")
            status = (
                enums.OrderStatus.COMPLETED.value
                if success
                else enums.OrderStatus.FAILED.value
            )
            tag = f"signal:{signal.id}:{subscriber.id}"
            order = models.Order(
                tag=tag,
                instrument_id=signal.instrument_id,
                trading_symbol=signal.trading_symbol,
                side=signal.side,
                quantity=quantity,
                price=signal.price,
                status=status,
                broker_order_id=broker_order_id,
                filled_quantity=quantity if success else 0,
                average_price=signal.price if success else 0,
                parent_tag=f"signal:{signal.id}",
                signal_id=signal.id,
                api_id=subscriber.id,
                meta_data=json.dumps(
                    {"signal_id": signal.id, "order": order_details, "response": response},
                    separators=(",", ":"),
                    ensure_ascii=True,
                ),
            )
            db.add(order)
            placed_orders.append(
                {
                    "subscriber_id": subscriber.id,
                    "broker_order_id": broker_order_id,
                    "status": status,
                }
            )

        await db.commit()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data={"signal": model_to_dict(signal), "orders": placed_orders},
            message="Signal processed",
        )


async def list_signals_data():
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.Signal))
        signals = result.scalars().all()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_list_to_dict(signals),
            message="Signals fetched",
        )


async def get_signal_data(signal_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.Signal).where(models.Signal.id == signal_id))
        signal = result.scalars().one_or_none()
        if not signal:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="Signal not found")
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(signal),
            message="Signal fetched",
        )
