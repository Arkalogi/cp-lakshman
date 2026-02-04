import json
import logging
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.commons import enums
from api.commons.schemas import ResponseSchema
from api.commons.utils import model_list_to_dict, model_to_dict
from api.data import database, models, red, utils
from api.demat_apis.paper import PaperAPI
from api.signals.schemas import SignalCreateSchema

logger = logging.getLogger(__name__)


async def add_signal_data(signal_data: SignalCreateSchema):
    async with database.DbAsyncSession() as db:
        instrument = utils.get_instrument_by_id(signal_data.instrument_id)
        if not instrument:
            return ResponseSchema(
                status=enums.ResponseStatus.ERROR,
                message="Invalid instrument ID",
            )
        signal = models.Signal(
            strategy_id=signal_data.strategy_id,
            instrument_id=signal_data.instrument_id,
            trading_symbol=instrument.trading_symbol,
            side=signal_data.side,
            meta_data=signal_data.meta_data,
        )
        db.add(signal)
        await db.commit()
        await db.refresh(signal)
        try:
            order_signal = {
                "signal_id": signal.id,
                "target_id": signal.strategy_id,
                "instrument_id": signal.instrument_id,
                "trading_symbol": signal.trading_symbol,
                "side": signal.side.value,
                "meta_data": signal.meta_data,
            }
            await red.get_async_redis().rpush(
                red.ORDER_SIGNAL_LIST,
                json.dumps(order_signal, separators=(",", ":"), ensure_ascii=True),
            )
        except Exception:
            logger.exception("Failed to enqueue signal %s", signal.id)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(signal),
            message="Signal created",
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
