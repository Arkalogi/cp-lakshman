from typing import Optional

from pydantic import BaseModel


class StrategySubscriptionCreateSchema(BaseModel):
    subscriber_id: int
    target_id: int


class StrategySubscriptionUpdateSchema(BaseModel):
    subscriber_id: Optional[int] = None
    target_id: Optional[int] = None
