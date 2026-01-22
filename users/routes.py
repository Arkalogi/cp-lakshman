from fastapi import APIRouter, HTTPException
from api.users import schemas

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=schemas.ResponseSchema)
async def register_user(user_data: schemas.UserRegisterSchema):
    try:
        response = await get_user_data(current_user)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
