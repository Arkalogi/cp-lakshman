from sqlalchemy import select
from api.commons import enums
from api.data import database
from api.data import models
from api.users.schemas import UserRegisterSchema, ResponseSchema


async def add_user_data(user_data: UserRegisterSchema):
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
            data=new_user,
            message="User registered",
        )


async def remove_user_data(user_id: str):
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.User).where(models.User.id == user_id))
        user = result.scalars().one_or_none()
        if not user:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="User not found")
