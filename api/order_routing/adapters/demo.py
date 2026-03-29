import uuid

from api.commons import enums
from api.data import models
from api.order_routing.adapters.base import BrokerAdapter, BrokerExecutionResult


class DemoBrokerAdapter(BrokerAdapter):
    provider_name = "demo"

    async def place_order(
        self, order: models.Order, demat_api: models.DematApi
    ) -> BrokerExecutionResult:
        return BrokerExecutionResult(
            broker_order_id=f"demo-{order.id}-{uuid.uuid4().hex[:10]}",
            status=enums.OrderStatus.COMPLETED.value,
            filled_quantity=int(order.quantity or 0),
            average_price=float(order.price or 0),
        )
