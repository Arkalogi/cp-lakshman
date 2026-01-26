from typing import Optional

from pydantic import BaseModel


class DematApiSubscriptionCreateSchema(BaseModel):
    subscriber_id: int
    target_id: int
    multiplier: Optional[float] = 1.0


class DematApiSubscriptionUpdateSchema(BaseModel):
    subscriber_id: Optional[int] = None
    target_id: Optional[int] = None
