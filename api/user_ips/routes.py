from fastapi import APIRouter, HTTPException

from api.commons.schemas import ResponseSchema
from api.user_ips import schemas, service

router = APIRouter(prefix="/user-ips", tags=["User IPs"])


@router.get("/", response_model=ResponseSchema)
async def list_user_ips():
    try:
        return await service.list_user_ips_data()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{user_id}", response_model=ResponseSchema)
async def get_user_ip_by_user(user_id: int):
    try:
        return await service.get_user_ip_by_user_data(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{ip_id}", response_model=ResponseSchema)
async def get_user_ip(ip_id: int):
    try:
        return await service.get_user_ip_data(ip_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", response_model=ResponseSchema)
async def create_user_ip(ip_data: schemas.UserIpCreateSchema):
    try:
        return await service.add_user_ip_data(ip_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{ip_id}", response_model=ResponseSchema)
async def modify_user_ip(ip_id: int, ip_data: schemas.UserIpUpdateSchema):
    try:
        return await service.update_user_ip_data(ip_id, ip_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{ip_id}", response_model=ResponseSchema)
async def delete_user_ip(ip_id: int):
    try:
        return await service.remove_user_ip_data(ip_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
