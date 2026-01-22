from typing import Optional

from pydantic import BaseModel


class StrategyCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None
    config: Optional[str] = None
    user_id: int


class StrategyUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[str] = None
    user_id: Optional[int] = None
