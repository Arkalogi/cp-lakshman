from fastapi import APIRouter, HTTPException

from api.commons.schemas import ResponseSchema
from api.users import schemas, service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=ResponseSchema)
async def list_users():
    try:
        return await service.list_users_data()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{user_id}", response_model=ResponseSchema)
async def get_user(user_id: int):
    try:
        return await service.get_user_data(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", response_model=ResponseSchema)
async def register_user(user_data: schemas.UserCreateSchema):
    try:
        return await service.add_user_data(user_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{user_id}", response_model=ResponseSchema)
async def modify_user(user_id: int, user_data: schemas.UserUpdateSchema):
    try:
        return await service.update_user_data(user_id, user_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{user_id}", response_model=ResponseSchema)
async def delete_user(user_id: int):
    try:
        return await service.remove_user_data(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
