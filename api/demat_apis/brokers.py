from __future__ import annotations

import logging
from typing import Any, Dict, Protocol

from api.commons import enums
from api.data import models
from api.demat_apis.paper import PaperAPI
from api.demat_apis.upstox import UpstoxApi

logger = logging.getLogger(__name__)


class BrokerClient(Protocol):
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


class UpstoxBroker:
    def __init__(self, api_id: int, config: Dict[str, Any]):
        self.api = UpstoxApi(
            api_id=api_id,
            api_key=config.get("api_key") or "",
            api_secret=config.get("api_secret") or "",
            redirect_url=config.get("redirect_url") or "",
            mobile_number=config.get("mobile_number") or "",
            totp_secret=config.get("totp_secret") or "",
            pin=config.get("pin") or "",
        )
        self.logged_in = False

    async def ensure_login(self) -> None:
        if self.logged_in:
            return
        logger.info("Upstox login placeholder for api_id=%s", self.api.api_id)
        self.logged_in = True

    async def place_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        await self.ensure_login()
        logger.info("Upstox place_order stub for order %s", order.get("signal_id"))
        return {"status": "error", "message": "Upstox place_order not implemented"}

    async def get_order_status(self, broker_order_id: str) -> Dict[str, Any]:
        await self.ensure_login()
        logger.info("Upstox get_order_status stub for order_id %s", broker_order_id)
        return {
            "status": "pending",
            "filled_quantity": 0,
            "average_price": 0,
        }


class ZerodhaBroker:
    def __init__(self, api_id: int, config: Dict[str, Any]):
        self.api_id = api_id
        self.config = config
        self.logged_in = False

    async def ensure_login(self) -> None:
        if self.logged_in:
            return
        logger.info("Zerodha login placeholder for api_id=%s", self.api_id)
        self.logged_in = True

    async def place_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        await self.ensure_login()
        logger.info("Zerodha place_order stub for order %s", order.get("signal_id"))
        return {"status": "error", "message": "Zerodha place_order not implemented"}

    async def get_order_status(self, broker_order_id: str) -> Dict[str, Any]:
        await self.ensure_login()
        logger.info("Zerodha get_order_status stub for order_id %s", broker_order_id)
        return {
            "status": "pending",
            "filled_quantity": 0,
            "average_price": 0,
        }


class AngelOneBroker:
    def __init__(self, api_id: int, config: Dict[str, Any]):
        self.api_id = api_id
        self.config = config
        self.logged_in = False

    async def ensure_login(self) -> None:
        if self.logged_in:
            return
        logger.info("AngelOne login placeholder for api_id=%s", self.api_id)
        self.logged_in = True

    async def place_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        await self.ensure_login()
        logger.info("AngelOne place_order stub for order %s", order.get("signal_id"))
        return {"status": "error", "message": "AngelOne place_order not implemented"}

    async def get_order_status(self, broker_order_id: str) -> Dict[str, Any]:
        await self.ensure_login()
        logger.info("AngelOne get_order_status stub for order_id %s", broker_order_id)
        return {
            "status": "pending",
            "filled_quantity": 0,
            "average_price": 0,
        }


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

    if demat_provider == enums.DematProvider.UPSTOX:
        return UpstoxBroker(demat_api.id, config)
    if demat_provider == enums.DematProvider.ZERODHA:
        return ZerodhaBroker(demat_api.id, config)
    if demat_provider == enums.DematProvider.ANGELONE:
        return AngelOneBroker(demat_api.id, config)
    return PaperBroker(demat_api.id, config)
