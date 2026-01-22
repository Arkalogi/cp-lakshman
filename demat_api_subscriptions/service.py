from sqlalchemy import select

from api.commons import enums
from api.commons.schemas import ResponseSchema
from api.commons.utils import model_to_dict, update_dict_from_schema
from api.data import database, models
from api.demat_api_subscriptions.schemas import (
    DematApiSubscriptionCreateSchema,
    DematApiSubscriptionUpdateSchema,
)


async def add_demat_api_subscription_data(subscription_data: DematApiSubscriptionCreateSchema):
    async with database.DbAsyncSession() as db:
        new_subscription = models.DematApiSubscription(
            subscriber_id=subscription_data.subscriber_id,
            target_id=subscription_data.target_id,
        )
        db.add(new_subscription)
        await db.commit()
        await db.refresh(new_subscription)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(new_subscription),
            message="Demat API subscription created",
        )


async def update_demat_api_subscription_data(
    subscription_id: int, subscription_data: DematApiSubscriptionUpdateSchema
):
    async with database.DbAsyncSession() as db:
        result = await db.execute(
            select(models.DematApiSubscription).where(
                models.DematApiSubscription.id == subscription_id
            )
        )
        subscription = result.scalars().one_or_none()
        if not subscription:
            return ResponseSchema(
                status=enums.ResponseStatus.ERROR, message="Demat API subscription not found"
            )

        update_data = update_dict_from_schema(subscription_data)
        for key, value in update_data.items():
            setattr(subscription, key, value)

        await db.commit()
        await db.refresh(subscription)
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data=model_to_dict(subscription),
            message="Demat API subscription updated",
        )


async def remove_demat_api_subscription_data(subscription_id: int):
    async with database.DbAsyncSession() as db:
        result = await db.execute(
            select(models.DematApiSubscription).where(
                models.DematApiSubscription.id == subscription_id
            )
        )
        subscription = result.scalars().one_or_none()
        if not subscription:
            return ResponseSchema(
                status=enums.ResponseStatus.ERROR, message="Demat API subscription not found"
            )

        await db.delete(subscription)
        await db.commit()
        return ResponseSchema(
            status=enums.ResponseStatus.SUCCESS,
            data={"id": subscription_id},
            message="Demat API subscription deleted",
        )
