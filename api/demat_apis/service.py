from sqlalchemy import select

from api.commons import enums
from api.commons.schemas import ResponseSchema
from api.commons.utils import model_list_to_dict, model_to_dict, update_dict_from_schema
from api.data import database, models
from api.demat_apis.schemas import DematApiCreateSchema, DematApiUpdateSchema


async def add_demat_api_data(api_data: DematApiCreateSchema):
    async with database.DbAsyncSession() as db:
        config = api_data.config
        if hasattr(config, "model_dump"):
            config = config.model_dump(mode="json")
        new_api = models.DematApi(
            config=config,
            user_id=api_data.user_id,
        )
        db.add(new_api)
        await db.commit()
        await db.refresh(new_api)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(new_api),
            message="Demat API created",
        )


async def get_demat_api_data(api_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.DematApi).where(models.DematApi.id == api_id))
        demat_api = result.scalars().one_or_none()
        if not demat_api:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="Demat API not found")
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(demat_api),
            message="Demat API fetched",
        )


async def list_demat_apis_data():
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.DematApi))
        demat_apis = result.scalars().all()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_list_to_dict(demat_apis),
            message="Demat APIs fetched",
        )


async def update_demat_api_data(api_id: int, api_data: DematApiUpdateSchema):
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.DematApi).where(models.DematApi.id == api_id))
        demat_api = result.scalars().one_or_none()
        if not demat_api:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="Demat API not found")

        update_data = update_dict_from_schema(api_data)
        if "config" in update_data and hasattr(update_data["config"], "model_dump"):
            update_data["config"] = update_data["config"].model_dump(mode="json")
        for key, value in update_data.items():
            setattr(demat_api, key, value)

        await db.commit()
        await db.refresh(demat_api)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(demat_api),
            message="Demat API updated",
        )


async def remove_demat_api_data(api_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.DematApi).where(models.DematApi.id == api_id))
        demat_api = result.scalars().one_or_none()
        if not demat_api:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="Demat API not found")

        await db.delete(demat_api)
        await db.commit()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data={"id": api_id},
            message="Demat API deleted",
        )
