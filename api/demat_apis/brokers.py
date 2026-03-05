from __future__ import annotations

import logging
from typing import Any, Dict, Protocol

from api.commons import enums
from api.data import models
from api.demat_apis.paper import PaperAPI
from api.demat_apis.upstox import UpstoxApi

logger = logging.getLogger(__name__)


class BrokerClient(Protocol):
    async def ensure_login(self) -> None:
        ...

    async def place_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        ...

    async def get_order_status(self, broker_order_id: str) -> Dict[str, Any]:
        ...


def _coerce_enum(enum_cls, value, default):
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str) and value in enum_cls._value2member_map_:
        return enum_cls(value)
    return default


class PaperBroker:
    def __init__(self, api_id: int, config: Dict[str, Any]):
        self.api = PaperAPI(
            api_id=str(api_id),
            api_key=config.get("api_key") or "",
            api_secret=config.get("api_secret") or "",
        )
        self.logged_in = False

    async def ensure_login(self) -> None:
        if self.logged_in:
            return
        await self.api.login()
        self.logged_in = True

    async def place_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        await self.ensure_login()
        return await self.api.place_order(order)

    async def get_order_status(self, broker_order_id: str) -> Dict[str, Any]:
        await self.ensure_login()
        result = await self.api.get_order_last_update(broker_order_id)
        if result.get("status") != "success":
            return {"status": "error", "message": result.get("message")}
        return {
            "status": "pending",
            "filled_quantity": 0,
            "average_price": 0,
            "details": result.get("details"),
        }


def build_broker_client(demat_api: models.DematApi) -> BrokerClient:
    config = demat_api.config or {}
    if not isinstance(config, dict):
        logger.warning("Unexpected demat_api config type: %s", type(config))
        config = {}

    demat_provider = _coerce_enum(
        enums.DematProvider, config.get("demat_provider"), enums.DematProvider.ARKALOGI
    )

    if (demat_provider == enums.DematProvider.ARKALOGI)and demat_api:
        return PaperAPI(demat_api.id, config)
    return PaperBroker(demat_api.id, config)
