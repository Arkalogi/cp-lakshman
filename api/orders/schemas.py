from typing import Optional

from pydantic import BaseModel

from api.commons import enums


class OrderStatusUpdateSchema(BaseModel):
    status: Optional[enums.OrderStatus] = None
    filled_quantity: Optional[int] = None
    average_price: Optional[float] = None
    broker_order_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
