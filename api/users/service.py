from sqlalchemy import select
from api.commons import enums
from api.commons.schemas import ResponseSchema
from api.commons.utils import model_to_dict, update_dict_from_schema
from api.data import database
from api.data import models
from api.users.schemas import UserCreateSchema, UserUpdateSchema


async def add_user_data(user_data: UserCreateSchema):
    async with database.DbAsyncSession() as db:
        new_user = models.User(
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            username=user_data.username,
            email=user_data.email,
            phone=user_data.phone,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(new_user),
            message="User registered",
        )


async def update_user_data(user_id: int, user_data: UserUpdateSchema):
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.User).where(models.User.id == user_id))
        user = result.scalars().one_or_none()
        if not user:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="User not found")

        update_data = update_dict_from_schema(user_data)
        for key, value in update_data.items():
            setattr(user, key, value)

        await db.commit()
        await db.refresh(user)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(user),
            message="User updated",
        )


async def remove_user_data(user_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.User).where(models.User.id == user_id))
        user = result.scalars().one_or_none()
        if not user:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="User not found")
        await db.delete(user)
        await db.commit()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data={"id": user_id},
            message="User deleted",
        )
