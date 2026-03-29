from typing import Optional

from pydantic import BaseModel


class StrategySubscriptionCreateSchema(BaseModel):
    subscriber_id: int
    target_id: int
    total_fund: float = 0
    fund_allocation_precentage: float = 1
    fund_deployed: float = 0


class StrategySubscriptionUpdateSchema(BaseModel):
    subscriber_id: Optional[int] = None
    target_id: Optional[int] = None
    total_fund: Optional[float] = None
    fund_allocation_precentage: Optional[float] = None
    fund_deployed: Optional[float] = None
