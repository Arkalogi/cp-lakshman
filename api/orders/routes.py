from fastapi import APIRouter, HTTPException

from api.commons.schemas import ResponseSchema
from api.orders import service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("/", response_model=ResponseSchema)
async def list_orders(limit: int = 50, offset: int = 0):
    try:
        return await service.list_orders_data(limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{order_id}", response_model=ResponseSchema)
async def get_order(order_id: int):
    try:
        return await service.get_order_data(order_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

