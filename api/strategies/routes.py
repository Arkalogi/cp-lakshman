from fastapi import APIRouter, HTTPException

from api.commons.schemas import ResponseSchema
from api.strategies import schemas, service

router = APIRouter(prefix="/strategies", tags=["Strategies"])


@router.post("/", response_model=ResponseSchema)
async def create_strategy(strategy_data: schemas.StrategyCreateSchema):
    try:
        return await service.add_strategy_data(strategy_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{strategy_id}", response_model=ResponseSchema)
async def modify_strategy(strategy_id: int, strategy_data: schemas.StrategyUpdateSchema):
    try:
        return await service.update_strategy_data(strategy_id, strategy_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{strategy_id}", response_model=ResponseSchema)
async def delete_strategy(strategy_id: int):
    try:
        return await service.remove_strategy_data(strategy_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
