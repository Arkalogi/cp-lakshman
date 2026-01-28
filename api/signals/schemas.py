from typing import Optional

from pydantic import BaseModel

from api.commons import enums


class SignalCreateSchema(BaseModel):
    strategy_id: int
    instrument_id: str
    trading_symbol: str
    side: enums.OrderSide
    quantity: int
    price: float
    meta_data: Optional[str] = None

