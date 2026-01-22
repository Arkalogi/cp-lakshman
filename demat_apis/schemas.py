from typing import Optional

from pydantic import BaseModel


class DematApiCreateSchema(BaseModel):
    config: str
    user_id: int = None


class DematApiUpdateSchema(BaseModel):
    config: Optional[str] = None
    user_id: Optional[int] = None
