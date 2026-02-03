from fastapi import APIRouter, HTTPException

from api.commons.schemas import ResponseSchema
from api.orders import service, schemas

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("/", response_model=ResponseSchema)
async def list_orders(limit: int = 50, offset: int = 0):
    try:
        return await service.list_orders_data(limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/children", response_model=ResponseSchema)
async def list_child_orders(
    signal_id: int | None = None,
    parent_tag: str | None = None,
    status: str | None = None,
):
    try:
        return await service.list_child_orders_data(
            signal_id=signal_id, parent_tag=parent_tag, status=status
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{order_id}", response_model=ResponseSchema)
async def get_order(order_id: int):
    try:
        return await service.get_order_data(order_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{order_id}/status", response_model=ResponseSchema)
async def update_order_status(
    order_id: int, update_data: schemas.OrderStatusUpdateSchema
):
    try:
        return await service.update_order_status_data(order_id, update_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
