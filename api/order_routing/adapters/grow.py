import uuid

from api.commons import enums
from api.data import models
from api.order_routing.adapters.base import BrokerAdapter, BrokerExecutionResult


class GrowBrokerAdapter(BrokerAdapter):
    provider_name = "grow"

    async def place_order(
        self, order: models.Order, demat_api: models.DematApi
    ) -> BrokerExecutionResult:
        config = demat_api.config or {}
        self._require_config_keys(config, ["api_key", "api_secret"])
        return BrokerExecutionResult(
            broker_order_id=f"grow-{order.id}-{uuid.uuid4().hex[:10]}",
            status=enums.OrderStatus.PENDING.value,
            filled_quantity=0,
            average_price=0,
        )
