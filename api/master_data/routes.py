from typing import Optional

from fastapi import APIRouter, Query

from api.commons import enums
from api.commons.schemas import ResponseSchema
from api.commons.utils import model_list_to_dict, model_to_dict
from api.data.local import MASTER_DATA, TOKEN_MAP


router = APIRouter(prefix="/master-data", tags=["Master Data"])


def _filter_instruments(
    instrument_id: Optional[str],
    trading_symbol: Optional[str],
    exchange: Optional[str],
    instrument_type: Optional[str],
    underlying: Optional[str],
):
    if instrument_id:
        instrument = MASTER_DATA.get(instrument_id)
        return [instrument] if instrument else []
    if trading_symbol:
        token = TOKEN_MAP.get(trading_symbol)
        instrument = MASTER_DATA.get(token) if token else None
        return [instrument] if instrument else []

    instruments = list(MASTER_DATA.values())
    if exchange:
        exchange_lower = exchange.lower()
        instruments = [
            instrument
            for instrument in instruments
            if instrument.exchange and instrument.exchange.value == exchange_lower
        ]
    if instrument_type:
        instrument_type_lower = instrument_type.lower()
        instruments = [
            instrument
            for instrument in instruments
            if instrument.instrument_type
            and instrument.instrument_type.value == instrument_type_lower
        ]
    if underlying:
        underlying_upper = underlying.upper()
        instruments = [
            instrument
            for instrument in instruments
            if instrument.underlying and instrument.underlying.upper() == underlying_upper
        ]
    return instruments


@router.get("/", response_model=ResponseSchema)
async def list_master_data(
    exchange: Optional[str] = None,
    instrument_type: Optional[str] = None,
    underlying: Optional[str] = None,
    trading_symbol: Optional[str] = None,
    instrument_id: Optional[str] = None,
):
    if not MASTER_DATA:
        return ResponseSchema(
            status=enums.ResponseStatus.ERROR,
            message="Master data not loaded",
        )
    instruments = _filter_instruments(
        instrument_id=instrument_id,
        trading_symbol=trading_symbol,
        exchange=exchange,
        instrument_type=instrument_type,
        underlying=underlying,
    )
    return ResponseSchema(
        status=enums.ResponseStatus.SUCCESS,
        data={
            "items": model_list_to_dict(instruments),
            "total": len(instruments),
        },
        message="Master data fetched",
    )


@router.get("/{instrument_id}", response_model=ResponseSchema)
async def get_master_data(instrument_id: str):
    instrument = MASTER_DATA.get(instrument_id)
    if not instrument:
        return ResponseSchema(
            status=enums.ResponseStatus.ERROR,
            message="Instrument not found",
        )
    return ResponseSchema(
        status=enums.ResponseStatus.SUCCESS,
        data=model_to_dict(instrument),
        message="Master data fetched",
    )
