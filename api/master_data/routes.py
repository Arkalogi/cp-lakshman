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
