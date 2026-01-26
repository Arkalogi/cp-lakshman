from sqlalchemy import select, or_, func

from api.commons import enums
from api.commons.schemas import ResponseSchema
from api.commons.utils import model_list_to_dict, model_to_dict
from api.data import database, models


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


async def list_subscriber_orders_data(order_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.Order).where(models.Order.id == order_id))
        order = result.scalars().one_or_none()
        if not order:
            return ResponseSchema(status=enums.ResponseStatus.ERROR, message="Order not found")

        subscriber_result = await db.execute(
            select(models.SubscriberOrder).where(
                or_(
                    models.SubscriberOrder.parent_order_id == order.id,
                    models.SubscriberOrder.parent_tag == order.tag,
                )
            )
        )
        subscriber_orders = subscriber_result.scalars().all()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_list_to_dict(subscriber_orders),
            message="Subscriber orders fetched",
        )
