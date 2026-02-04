from typing import Optional

from pydantic import BaseModel

from api.commons import enums


class SignalCreateSchema(BaseModel):
    type: enums.SignalType
    strategy_id: int
    instrument_id: str
    side: enums.OrderSide
    depends_on_signal_id: Optional[int] = None
    meta_data: Optional[str] = None

