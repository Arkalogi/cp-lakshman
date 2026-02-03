from fastapi import APIRouter, HTTPException

from api.commons.schemas import ResponseSchema
from api.watchlists import schemas, service

router = APIRouter(prefix="/watchlists", tags=["Watchlists"])


@router.get("/", response_model=ResponseSchema)
async def list_watchlists():
    try:
        return await service.list_watchlists_data()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{watchlist_id}", response_model=ResponseSchema)
async def get_watchlist(watchlist_id: int):
    try:
        return await service.get_watchlist_data(watchlist_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", response_model=ResponseSchema)
async def create_watchlist(watchlist_data: schemas.WatchlistCreateSchema):
    try:
        return await service.add_watchlist_data(watchlist_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{watchlist_id}", response_model=ResponseSchema)
async def modify_watchlist(
    watchlist_id: int, watchlist_data: schemas.WatchlistUpdateSchema
):
    try:
        return await service.update_watchlist_data(watchlist_id, watchlist_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{watchlist_id}", response_model=ResponseSchema)
async def delete_watchlist(watchlist_id: int):
    try:
        return await service.remove_watchlist_data(watchlist_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{watchlist_id}/items", response_model=ResponseSchema)
async def add_watchlist_item(
    watchlist_id: int, instrument_id: int
):
    try:
        return await service.add_instrument_to_watchlist(watchlist_id, instrument_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))