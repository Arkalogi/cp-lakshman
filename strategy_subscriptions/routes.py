from fastapi import APIRouter, HTTPException

from api.commons.schemas import ResponseSchema
from api.strategy_subscriptions import schemas, service

router = APIRouter(prefix="/strategy-subscriptions", tags=["Strategy Subscriptions"])


@router.post("/", response_model=ResponseSchema)
async def create_strategy_subscription(
    subscription_data: schemas.StrategySubscriptionCreateSchema,
):
    try:
        return await service.add_strategy_subscription_data(subscription_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{subscription_id}", response_model=ResponseSchema)
async def modify_strategy_subscription(
    subscription_id: int, subscription_data: schemas.StrategySubscriptionUpdateSchema
):
    try:
        return await service.update_strategy_subscription_data(
            subscription_id, subscription_data
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{subscription_id}", response_model=ResponseSchema)
async def delete_strategy_subscription(subscription_id: int):
    try:
        return await service.remove_strategy_subscription_data(subscription_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
