from typing import Any, Optional

from pydantic import BaseModel

from api.commons import enums


class ResponseSchema(BaseModel):
    status: enums.ResponseStatus
    data: Optional[Any] = None
    message: str
