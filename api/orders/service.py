from sqlalchemy import select, func

from api.commons import enums
from api.commons.schemas import ResponseSchema
from api.commons.utils import model_list_to_dict, model_to_dict, update_dict_from_schema
from api.data import database, models
from api.orders.schemas import OrderStatusUpdateSchema


async def list_orders_data(limit: int = 50, offset: int = 0):
    async with database.DbAsyncSession() as db:
        total_result = await db.execute(select(func.count()).select_from(models.Order))
        total = total_result.scalar_one()
        result = await db.execute(
            select(models.Order)
            .order_by(models.Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        orders = result.scalars().all()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data={
                "items": model_list_to_dict(orders),
                "total": total,
                "limit": limit,
                "offset": offset,
            },
            message="Orders fetched",
        )


async def list_child_orders_data(
    signal_id: int | None = None,
    parent_tag: str | None = None,
    status: str | None = None,
):
    async with database.DbAsyncSession() as db:
        query = select(models.Order).order_by(models.Order.created_at.desc())
        if signal_id is not None:
            query = query.where(models.Order.signal_id == signal_id)
        if parent_tag is not None:
            query = query.where(models.Order.parent_tag == parent_tag)
        if status is not None:
            query = query.where(models.Order.status == status)
        result = await db.execute(query)
        orders = result.scalars().all()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_list_to_dict(orders),
            message="Child orders fetched",
        )


async def get_order_data(order_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.Order).where(models.Order.id == order_id))
        order = result.scalars().one_or_none()
        if not order:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="Order not found")
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(order),
            message="Order fetched",
        )


async def update_order_status_data(order_id: int, update_data: OrderStatusUpdateSchema):
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.Order).where(models.Order.id == order_id))
        order = result.scalars().one_or_none()
        if not order:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="Order not found")

        payload = update_dict_from_schema(update_data)
        if "status" in payload and payload["status"] is not None:
            payload["status"] = payload["status"].value

        for key, value in payload.items():
            if value is not None:
                setattr(order, key, value)

        db.add(order)
        await db.commit()
        await db.refresh(order)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(order),
            message="Order status updated",
        )
