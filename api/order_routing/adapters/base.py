from dataclasses import dataclass

from api.data import models


@dataclass
class BrokerExecutionResult:
    broker_order_id: str
    status: str
    filled_quantity: int
    average_price: float
    error_code: str | None = None
    error_message: str | None = None


class BrokerAdapter:
    provider_name = "broker"

    async def place_order(
        self, order: models.Order, demat_api: models.DematApi
    ) -> BrokerExecutionResult:
        raise NotImplementedError

    def _require_config_keys(self, config: dict, required_keys: list[str]) -> None:
        missing = [key for key in required_keys if not config.get(key)]
        if missing:
            raise ValueError(
                f"{self.provider_name} config missing required fields: {', '.join(missing)}"
            )
