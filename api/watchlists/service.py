from sqlalchemy import select
import logging

from api.commons import enums
from api.commons.schemas import ResponseSchema
from api.commons.utils import model_list_to_dict, model_to_dict, update_dict_from_schema
from api.data import database, models
from api.watchlists.schemas import WatchlistCreateSchema, WatchlistUpdateSchema

logger = logging.getLogger(__name__)


async def add_watchlist_data(watchlist_data: WatchlistCreateSchema):
    async with database.DbAsyncSession() as db:
        new_watchlist = models.Watchlist(
            name=watchlist_data.name,
            description=watchlist_data.description,
            user_id=watchlist_data.user_id,
        )
        db.add(new_watchlist)
        await db.commit()
        await db.refresh(new_watchlist)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(new_watchlist),
            message="Watchlist created",
        )
    
async def get_watchlist_data(watchlist_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.Watchlist).where(models.Watchlist.id == watchlist_id))
        watchlist = result.scalars().one_or_none()
        if not watchlist:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="Watchlist not found")
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(watchlist),
            message="Watchlist fetched",
        )
    
async def list_watchlists_data():
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.Watchlist))
        watchlists = result.scalars().all()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_list_to_dict(watchlists),
            message="Watchlists fetched",
        )
    
async def update_watchlist_data(watchlist_id: int, watchlist_data: WatchlistUpdateSchema):
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.Watchlist).where(models.Watchlist.id == watchlist_id))
        watchlist = result.scalars().one_or_none()
        if not watchlist:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="Watchlist not found")
        update_dict_from_schema(watchlist, watchlist_data)
        db.add(watchlist)
        await db.commit()
        await db.refresh(watchlist)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(watchlist),
            message="Watchlist updated",
        )
    
async def remove_watchlist_data(watchlist_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.Watchlist).where(models.Watchlist.id == watchlist_id))
        watchlist = result.scalars().one_or_none()
        if not watchlist:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="Watchlist not found")
        await db.delete(watchlist)
        await db.commit()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data={},
            message="Watchlist deleted",
        )
    
async def add_instrument_to_watchlist(watchlist_id: int, instrument_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.Watchlist).where(models.Watchlist.id == watchlist_id))
        watchlist = result.scalars().one_or_none()
        if not watchlist:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="Watchlist not found")
        
        result = await db.execute(select(models.Instrument).where(models.Instrument.id == instrument_id))
        instrument = result.scalars().one_or_none()
        if not instrument:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="Instrument not found")
        
        if instrument in watchlist.instruments:
            return ResponseSchema(
                status=enums.ResponseStatus.ERROR,
                message="Instrument already in watchlist",
            )
        
        watchlist.instruments.append(instrument)
        db.add(watchlist)
        await db.commit()
        await db.refresh(watchlist)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(watchlist),
            message="Instrument added to watchlist",
        )