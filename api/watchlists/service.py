from sqlalchemy import delete, select

from api.commons import enums
from api.commons.schemas import ResponseSchema
from api.commons.utils import model_list_to_dict, model_to_dict, update_dict_from_schema
from api.data import database, models, utils as data_utils
from api.watchlists.schemas import (
    WatchlistCreateSchema,
    WatchlistInstrumentAddSchema,
    WatchlistUpdateSchema,
)


async def _watchlist_payload(db, watchlist: models.Watchlist) -> dict:
    links_result = await db.execute(
        select(models.WatchlistInstrument).where(
            models.WatchlistInstrument.watchlist_id == watchlist.id
        )
    )
    links = links_result.scalars().all()
    instruments = []
    for link in links:
        payload = data_utils.get_instrument_payload_by_id(link.instrument_id)
        if payload:
            instruments.append(payload)
    base = model_to_dict(watchlist)
    base["items"] = instruments
    base["instrument_ids"] = [link.instrument_id for link in links]
    return base


async def add_watchlist_data(watchlist_data: WatchlistCreateSchema):
    async with database.DbAsyncSession() as db:
        new_watchlist = models.Watchlist(
            name=watchlist_data.name,
            description=watchlist_data.description,
        )
        db.add(new_watchlist)
        await db.commit()
        await db.refresh(new_watchlist)

        for instrument_id in watchlist_data.instruments or []:
            db.add(
                models.WatchlistInstrument(
                    watchlist_id=new_watchlist.id,
                    instrument_id=str(instrument_id),
                )
            )
        if watchlist_data.instruments:
            await db.commit()

        payload = await _watchlist_payload(db, new_watchlist)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=payload,
            message="Watchlist created",
        )


async def get_watchlist_data(watchlist_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(
            select(models.Watchlist).where(models.Watchlist.id == watchlist_id)
        )
        watchlist = result.scalars().one_or_none()
        if not watchlist:
            return ResponseSchema(
                status=enums.ResponseStatus.ERROR, message="Watchlist not found"
            )
        payload = await _watchlist_payload(db, watchlist)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=payload,
            message="Watchlist fetched",
        )


async def list_watchlists_data():
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.Watchlist))
        watchlists = result.scalars().all()
        payload = []
        for watchlist in watchlists:
            payload.append(await _watchlist_payload(db, watchlist))
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=payload,
            message="Watchlists fetched",
        )


async def update_watchlist_data(watchlist_id: int, watchlist_data: WatchlistUpdateSchema):
    async with database.DbAsyncSession() as db:
        result = await db.execute(
            select(models.Watchlist).where(models.Watchlist.id == watchlist_id)
        )
        watchlist = result.scalars().one_or_none()
        if not watchlist:
            return ResponseSchema(
                status=enums.ResponseStatus.ERROR, message="Watchlist not found"
            )
        update_data = update_dict_from_schema(watchlist_data)
        for key, value in update_data.items():
            if value is not None:
                setattr(watchlist, key, value)
        db.add(watchlist)
        await db.commit()
        await db.refresh(watchlist)
        payload = await _watchlist_payload(db, watchlist)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=payload,
            message="Watchlist updated",
        )


async def remove_watchlist_data(watchlist_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(
            select(models.Watchlist).where(models.Watchlist.id == watchlist_id)
        )
        watchlist = result.scalars().one_or_none()
        if not watchlist:
            return ResponseSchema(
                status=enums.ResponseStatus.ERROR, message="Watchlist not found"
            )
        await db.delete(watchlist)
        await db.commit()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data={},
            message="Watchlist deleted",
        )


async def add_instrument_to_watchlist(
    watchlist_id: int, payload: WatchlistInstrumentAddSchema
):
    instrument_id = str(payload.instrument_id)
    async with database.DbAsyncSession() as db:
        result = await db.execute(
            select(models.Watchlist).where(models.Watchlist.id == watchlist_id)
        )
        watchlist = result.scalars().one_or_none()
        if not watchlist:
            return ResponseSchema(
                status=enums.ResponseStatus.ERROR, message="Watchlist not found"
            )

        if not data_utils.get_instrument_payload_by_id(instrument_id):
            return ResponseSchema(
                status=enums.ResponseStatus.ERROR, message="Instrument not found"
            )

        link_result = await db.execute(
            select(models.WatchlistInstrument).where(
                models.WatchlistInstrument.watchlist_id == watchlist_id,
                models.WatchlistInstrument.instrument_id == instrument_id,
            )
        )
        existing = link_result.scalars().one_or_none()
        if existing:
            return ResponseSchema(
                status=enums.ResponseStatus.ERROR,
                message="Instrument already in watchlist",
            )

        db.add(
            models.WatchlistInstrument(
                watchlist_id=watchlist_id,
                instrument_id=instrument_id,
            )
        )
        await db.commit()
        await db.refresh(watchlist)
        data = await _watchlist_payload(db, watchlist)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=data,
            message="Instrument added to watchlist",
        )


async def remove_instrument_from_watchlist(watchlist_id: int, instrument_id: str):
    async with database.DbAsyncSession() as db:
        result = await db.execute(
            select(models.Watchlist).where(models.Watchlist.id == watchlist_id)
        )
        watchlist = result.scalars().one_or_none()
        if not watchlist:
            return ResponseSchema(
                status=enums.ResponseStatus.ERROR, message="Watchlist not found"
            )

        delete_result = await db.execute(
            delete(models.WatchlistInstrument).where(
                models.WatchlistInstrument.watchlist_id == watchlist_id,
                models.WatchlistInstrument.instrument_id == instrument_id,
            )
        )
        await db.commit()
        if (delete_result.rowcount or 0) == 0:
            return ResponseSchema(
                status=enums.ResponseStatus.ERROR,
                message="Instrument not found in watchlist",
            )

        await db.refresh(watchlist)
        data = await _watchlist_payload(db, watchlist)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=data,
            message="Instrument removed from watchlist",
        )
