from fastapi import APIRouter, HTTPException

from api.commons.schemas import ResponseSchema
from api.signals import schemas, service
from api.orders import service as orders_service

router = APIRouter(prefix="/signals", tags=["Signals"])


@router.get("/", response_model=ResponseSchema)
async def list_signals():
    try:
        return await service.list_signals_data()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{signal_id}", response_model=ResponseSchema)
async def get_signal(signal_id: int):
    try:
        return await service.get_signal_data(signal_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", response_model=ResponseSchema)
async def create_signal(signal_data: schemas.SignalCreateSchema):
    try:
        return await service.add_signal_data(signal_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{signal_id}/orders", response_model=ResponseSchema)
async def list_signal_orders(signal_id: int, status: str | None = None):
    try:
        return await orders_service.list_child_orders_data(
            signal_id=signal_id, status=status
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
