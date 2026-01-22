from fastapi import APIRouter, HTTPException

from api.commons.schemas import ResponseSchema
from api.demat_apis import schemas, service

router = APIRouter(prefix="/demat-apis", tags=["Demat APIs"])


@router.get("/", response_model=ResponseSchema)
async def list_demat_apis():
    try:
        return await service.list_demat_apis_data()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{api_id}", response_model=ResponseSchema)
async def get_demat_api(api_id: int):
    try:
        return await service.get_demat_api_data(api_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", response_model=ResponseSchema)
async def create_demat_api(api_data: schemas.DematApiCreateSchema):
    try:
        return await service.add_demat_api_data(api_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{api_id}", response_model=ResponseSchema)
async def modify_demat_api(api_id: int, api_data: schemas.DematApiUpdateSchema):
    try:
        return await service.update_demat_api_data(api_id, api_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{api_id}", response_model=ResponseSchema)
async def delete_demat_api(api_id: int):
    try:
        return await service.remove_demat_api_data(api_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
