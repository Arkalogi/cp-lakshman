from pydantic import BaseModel
from api.commons import enums


class ResponseSchema(BaseModel):
    status: enums.ResponseStatus
    data: dict
    message: str


class UserRegisterSchema(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: str
    phone: str
