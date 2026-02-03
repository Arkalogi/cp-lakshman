from typing import Optional

from pydantic import BaseModel

from api.commons import enums


class SignalCreateSchema(BaseModel):
    strategy_id: int
    instrument_id: str
    side: enums.OrderSide
    meta_data: Optional[str] = None

