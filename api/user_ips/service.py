from sqlalchemy import select

from api.commons import enums
from api.commons.schemas import ResponseSchema
from api.commons.utils import model_list_to_dict, model_to_dict, update_dict_from_schema
from api.data import database, models
from api.user_ips.schemas import UserIpCreateSchema, UserIpUpdateSchema


def _normalize_ip_data(data: dict) -> dict:
    return {key: str(value) for key, value in data.items()}


async def add_user_ip_data(ip_data: UserIpCreateSchema):
    async with database.DbAsyncSession() as db:
        user_result = await db.execute(
            select(models.User).where(models.User.id == ip_data.user_id)
        )
        if not user_result.scalars().one_or_none():
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="User not found")

        existing_user_ip = await db.execute(
            select(models.UserIpAddress).where(
                models.UserIpAddress.user_id == ip_data.user_id
            )
        )
        if existing_user_ip.scalars().one_or_none():
            return ResponseSchema(
                status=enums.ResponseStatus.ERROR,
                message="User already has a static IP assigned",
            )

        static_ip = str(ip_data.static_ip)
        private_ip = str(ip_data.private_ip)
        conflict = await _find_ip_conflict(db, static_ip=static_ip, private_ip=private_ip)
        if conflict:
            return conflict

        new_user_ip = models.UserIpAddress(
            user_id=ip_data.user_id,
            static_ip=static_ip,
            private_ip=private_ip,
        )
        db.add(new_user_ip)
        await db.commit()
        await db.refresh(new_user_ip)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(new_user_ip),
            message="User IP assigned",
        )


async def get_user_ip_data(ip_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(
            select(models.UserIpAddress).where(models.UserIpAddress.id == ip_id)
        )
        user_ip = result.scalars().one_or_none()
        if not user_ip:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="User IP not found")
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(user_ip),
            message="User IP fetched",
        )


async def get_user_ip_by_user_data(user_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(
            select(models.UserIpAddress).where(models.UserIpAddress.user_id == user_id)
        )
        user_ip = result.scalars().one_or_none()
        if not user_ip:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="User IP not found")
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(user_ip),
            message="User IP fetched",
        )


async def list_user_ips_data():
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.UserIpAddress))
        user_ips = result.scalars().all()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_list_to_dict(user_ips),
            message="User IPs fetched",
        )


async def update_user_ip_data(ip_id: int, ip_data: UserIpUpdateSchema):
    async with database.DbAsyncSession() as db:
        result = await db.execute(
            select(models.UserIpAddress).where(models.UserIpAddress.id == ip_id)
        )
        user_ip = result.scalars().one_or_none()
        if not user_ip:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="User IP not found")

        update_data = _normalize_ip_data(update_dict_from_schema(ip_data))
        if "user_id" in update_data:
            update_data["user_id"] = int(update_data["user_id"])
            user_result = await db.execute(
                select(models.User).where(models.User.id == update_data["user_id"])
            )
            if not user_result.scalars().one_or_none():
                return ResponseSchema(
                    status=enums.ResponseStatus.ERROR, message="User not found"
                )
            existing_user_ip = await db.execute(
                select(models.UserIpAddress).where(
                    models.UserIpAddress.user_id == update_data["user_id"],
                    models.UserIpAddress.id != ip_id,
                )
            )
            if existing_user_ip.scalars().one_or_none():
                return ResponseSchema(
                    status=enums.ResponseStatus.ERROR,
                    message="User already has a static IP assigned",
                )

        static_ip = update_data.get("static_ip")
        private_ip = update_data.get("private_ip")
        conflict = await _find_ip_conflict(
            db,
            static_ip=static_ip,
            private_ip=private_ip,
            exclude_id=ip_id,
        )
        if conflict:
            return conflict

        for key, value in update_data.items():
            setattr(user_ip, key, value)

        await db.commit()
        await db.refresh(user_ip)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(user_ip),
            message="User IP updated",
        )


async def remove_user_ip_data(ip_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(
            select(models.UserIpAddress).where(models.UserIpAddress.id == ip_id)
        )
        user_ip = result.scalars().one_or_none()
        if not user_ip:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="User IP not found")
        await db.delete(user_ip)
        await db.commit()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data={"id": ip_id},
            message="User IP deleted",
        )


async def _find_ip_conflict(db, static_ip=None, private_ip=None, exclude_id=None):
    if static_ip:
        query = select(models.UserIpAddress).where(
            models.UserIpAddress.static_ip == static_ip
        )
        if exclude_id is not None:
            query = query.where(models.UserIpAddress.id != exclude_id)
        result = await db.execute(query)
        if result.scalars().one_or_none():
            return ResponseSchema(
                status=enums.ResponseStatus.ERROR,
                message="Static IP already assigned",
            )

    if private_ip:
        query = select(models.UserIpAddress).where(
            models.UserIpAddress.private_ip == private_ip
        )
        if exclude_id is not None:
            query = query.where(models.UserIpAddress.id != exclude_id)
        result = await db.execute(query)
        if result.scalars().one_or_none():
            return ResponseSchema(
                status=enums.ResponseStatus.ERROR,
                message="Private IP already assigned",
            )

    return None
