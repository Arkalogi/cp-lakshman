from fastapi import APIRouter, Query

from api.commons import enums
from api.commons.schemas import ResponseSchema
from api.data import utils

router = APIRouter(prefix="/master-data", tags=["Master Data"])


@router.get("/summary", response_model=ResponseSchema)
async def summary():
    return ResponseSchema(
        status=enums.ResponseStatus.SUCCESS,
        data={"count": utils.get_master_data_count()},
        message="Master data summary fetched",
    )


@router.get("/instruments/{instrument_id}", response_model=ResponseSchema)
async def by_id(instrument_id: str):
    instrument = utils.get_instrument_payload_by_id(instrument_id)
    if not instrument:
        return ResponseSchema(
            status=enums.ResponseStatus.ERROR,
            data=None,
            message="Instrument not found",
        )
    return ResponseSchema(
        status=enums.ResponseStatus.SUCCESS,
        data=instrument,
        message="Instrument fetched",
    )


@router.get("/search", response_model=ResponseSchema)
async def search(
    trading_symbol: str | None = Query(default=None),
    underlying: str | None = Query(default=None),
    exchange: str | None = Query(default=None),
    instrument_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    data = utils.search_instruments(
        trading_symbol=trading_symbol,
        underlying=underlying,
        exchange=exchange,
        instrument_type=instrument_type,
        limit=limit,
        offset=offset,
    )
    return ResponseSchema(
        status=enums.ResponseStatus.SUCCESS,
        data=data,
        message="Master data search completed",
    )


@router.get("/mapping/xts/{instrument_id}", response_model=ResponseSchema)
async def map_xts_to_upstox(instrument_id: str):
    upstox_key = utils.get_upstox_instrument_key_by_xts_id(instrument_id)
    if not upstox_key:
        return ResponseSchema(
            status=enums.ResponseStatus.ERROR,
            data=None,
            message="Mapping not found for XTS instrument_id",
        )
    return ResponseSchema(
        status=enums.ResponseStatus.SUCCESS,
        data={"instrument_id": instrument_id, "upstox_instrument_key": upstox_key},
        message="XTS to Upstox mapping fetched",
    )


@router.get("/mapping/upstox/{instrument_key}", response_model=ResponseSchema)
async def map_upstox_to_xts(instrument_key: str):
    xts_id = utils.get_xts_instrument_id_by_upstox_key(instrument_key)
    if not xts_id:
        return ResponseSchema(
            status=enums.ResponseStatus.ERROR,
            data=None,
            message="Mapping not found for Upstox instrument_key",
        )
    return ResponseSchema(
        status=enums.ResponseStatus.SUCCESS,
        data={"upstox_instrument_key": instrument_key, "instrument_id": xts_id},
        message="Upstox to XTS mapping fetched",
    )
