from fastapi import APIRouter, HTTPException

from api.commons.schemas import ResponseSchema
from api.demat_api_subscriptions import schemas, service

router = APIRouter(prefix="/demat-api-subscriptions", tags=["Demat API Subscriptions"])


@router.post("/", response_model=ResponseSchema)
async def create_demat_api_subscription(
    subscription_data: schemas.DematApiSubscriptionCreateSchema,
):
    try:
        return await service.add_demat_api_subscription_data(subscription_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{subscription_id}", response_model=ResponseSchema)
async def modify_demat_api_subscription(
    subscription_id: int, subscription_data: schemas.DematApiSubscriptionUpdateSchema
):
    try:
        return await service.update_demat_api_subscription_data(
            subscription_id, subscription_data
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{subscription_id}", response_model=ResponseSchema)
async def delete_demat_api_subscription(subscription_id: int):
    try:
        return await service.remove_demat_api_subscription_data(subscription_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
