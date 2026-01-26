import asyncio
import uuid
import requests
import pyotp
import base64
import websocket
import logging
import json
from typing import Dict
from api.commons import enums
from api.data import red
from urllib.parse import urlencode, urlparse, parse_qs

from api.data import database
from api.data.models import Order

logger = logging.getLogger(__name__)

UPSTOX_BASE_URL = "https://api.upstox.com/v2"
UPSTOX_SERVICE_URL = "https://service.upstox.com"

quantity_processed: Dict[str, int] = {}


class UpstoxApi:
    def __init__(
        self,
        api_id: int,
        api_key: str,
        api_secret: str,
        redirect_url: str,
        mobile_number: str,
        totp_secret: str,
        pin: str,
    ):
        self.api_id = api_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_url = redirect_url
        self.mobile_number = mobile_number
        self.totp_secret = totp_secret
        self.pin = pin
        self.original_orders: Dict[str, Order] = {}
        self.order_with_filled_quantity: Dict[str, Order] = {}
        self._filled_by_order: Dict[str, int] = {}
        self._loop = None

    async def start_order_update_socket(self, access_token: str):
        headers = {"Authorization": f"Bearer {access_token}"}
        self._loop = asyncio.get_running_loop()
        ws = websocket.WebSocketApp(
            "wss://api.upstox.com/v2/feed/portfolio-stream-feed?update_types=order",
            header=headers,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        await asyncio.to_thread(ws.run_forever, reconnect=5)
        logger.info("Order update socket disconnected, reconnecting")

    def login(self):
        livefeed_token = None
        livefeed_refresh_token = None
        access_token = None
        with requests.Session() as session:
            url = UPSTOX_BASE_URL + "/login/authorization/dialog"
            url = (
                UPSTOX_BASE_URL
                + "/login/authorization/dialog"
                + f"?{urlencode({
                    "client_id": self.api_key,
                    "redirect_uri": self.redirect_url,
                    "response_type": "code",
                    "scope": "general",
                    "state": "123",
                })}"
            )
            response = session.get(url=url, allow_redirects=False)
            user_id = parse_qs(urlparse(response.headers["location"]).query)["user_id"][0]
            client_id = parse_qs(urlparse(response.headers["location"]).query)["client_id"][
                0
            ]

            session.headers.update(
                {
                    "x-device-details": "platform=WEB|osName=Windows/10|osVersion=Chrome/131.0.0.0|appVersion=4.0.0|modelName=Chrome|manufacturer=unknown|uuid=YSBB6dKYEDtLd0gKuQhe|userAgent=Upstox 3.0 Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Content-Type": "application/json",
                }
            )

            url = UPSTOX_SERVICE_URL + "/login/open/v6/auth/1fa/otp/generate"
            payload = {"data": {"mobileNumber": self.mobile_number, "userId": user_id}}
            response = session.post(url, json=payload)
            validate_otp_token = response.json()["data"]["validateOTPToken"]
            totp = pyotp.TOTP(self.totp_secret)
            url = UPSTOX_SERVICE_URL + "/login/open/v4/auth/1fa/otp-totp/verify"
            payload = {"data": {"otp": totp.now(), "validateOtpToken": validate_otp_token}}
            response = session.post(url, json=payload, allow_redirects=False)

            encoded_pin = base64.b64encode(self.pin.encode("utf-8")).decode("utf-8")
            url = (
                UPSTOX_SERVICE_URL
                + f"/login/open/v3/auth/2fa?client_id={client_id}&redirect_uri=https%3A%2F%2Fapi-v2.upstox.com%2Flogin%2Fauthorization%2Fredirect"
            )
            payload = {"data": {"twoFAMethod": "SECRET_PIN", "inputText": encoded_pin}}
            response = session.post(url, json=payload)
            for cookie in response.cookies:
                if "access_token" in cookie.name:
                    livefeed_token = cookie.value
                if "refresh_token" in cookie.name:
                    livefeed_refresh_token = cookie.value
            url = (
                UPSTOX_SERVICE_URL
                + f"/login/v2/oauth/authorize?client_id={client_id}&redirect_uri=https%3A%2F%2Fapi-v2.upstox.com%2Flogin%2Fauthorization%2Fredirect&response_type=code"
            )
            payload = {"data": {"userOAuthApproval": True}}
            response = session.post(url, json=payload)
            code = parse_qs(urlparse(response.json()["data"]["redirectUri"]).query)["code"]
            url = UPSTOX_BASE_URL + "/login/authorization/token"
            headers = {
                "accept": "application/json",
                "Api-Version": "2.0",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            payload = {
                "code": code,
                "client_id": self.api_key,
                "client_secret": self.api_secret,
                "redirect_uri": self.redirect_url,
                "grant_type": "authorization_code",
            }
            response = requests.post(url, data=payload, headers=headers)
            access_token = response.json()["access_token"]
        logger.info(f"Upstox login successful for user_id={user_id}, client_id={client_id}, access_token={access_token}")
        return livefeed_token, livefeed_refresh_token, access_token


    def on_open(self, ws):
        logger.info("Order update socket is connected.")

    def on_message(self, ws, message: dict):
        logger.info("Message: %s", message)
        try:
            message_json = json.loads(message)
            update_type = message_json.get("update_type")
            if update_type != "order":
                return

            status = message_json.get("status")
            exchange = message_json.get("exchange")
            exchange_value = (
                exchange[0] if isinstance(exchange, list) and exchange else exchange
            )
            if exchange_value not in {"NFO", "BFO"}:
                return

            instrument_token = message_json["instrument_token"]
            instrument_id = instrument_token.split("|")[1]
            trading_symbol = message_json.get("trading_symbol")
            user_id = message_json.get("user_id")
            order_id = message_json.get("order_id")
            side = message_json.get("transaction_type")
            average_price = message_json.get("average_price")
            filled_quantity = int(float(message_json.get("filled_quantity") or 0))
            logger.info(
                "Order(id=%s user_id=%s instrument_id=%s status=%s side=%s average_price=%s filled_quantity=%s)",
                order_id,
                user_id,
                instrument_id,
                status,
                side,
                average_price,
                filled_quantity,
            )
            previous_filled = self._filled_by_order.get(order_id, 0)
            if filled_quantity <= previous_filled:
                return

            new_order_quantity = filled_quantity - previous_filled
            self._filled_by_order[order_id] = filled_quantity
            tag = str(uuid.uuid4())
            quantity_processed[tag] = new_order_quantity

            order = Order(
                tag=tag,
                instrument_token=instrument_token,
                trading_symbol=trading_symbol,
                side=_map_order_side(side),
                quantity=int(new_order_quantity),
                price=_coerce_price(average_price, message_json.get("price")),
                status=enums.OrderStatus.COMPLETED.value,
                broker_order_id=order_id,
                filled_quantity=int(new_order_quantity),
                average_price=_coerce_price(average_price, None),
                api_id=self.api_id,
                meta_data=json.dumps(message_json, separators=(",", ":"), ensure_ascii=True),
            )
            self.order_with_filled_quantity[tag] = order
            order_signal = {
                "target_id": self.api_id,
                "order_id": tag,
                "instrument_id": instrument_id,
                "trading_symbol": trading_symbol,
                "side": side,
                "average_price": average_price,
                "quantity": new_order_quantity,
                "status": enums.OrderStatus.PENDING.value,
            }
            red.get_redis().rpush(
                red.ORDER_SIGNAL_LIST,
                json.dumps(order_signal, separators=(",", ":"), ensure_ascii=True),
            )
            self._persist_order_async(order)
        except Exception:
            logger.exception("Failed to process order update message.")

    def on_error(self, ws, message: dict):
        logger.info(f"Order update error: {message}")

    def on_close(self, ws, message: dict):
        logger.info(f"Order update socket is closed")

    def _persist_order_async(self, order: Order):
        if not self._loop:
            logger.warning("No running event loop available for order persistence.")
            return
        asyncio.run_coroutine_threadsafe(self._persist_order(order), self._loop)

    async def _persist_order(self, order: Order):
        try:
            async with database.DbAsyncSession() as db:
                db.add(order)
                await db.commit()
                await db.refresh(order)
        except Exception:
            logger.exception("Failed to persist order %s", order.tag)


def _map_order_side(side: str) -> enums.OrderSide:
    side_value = (side or "").strip().lower()
    if side_value == "buy":
        return enums.OrderSide.BUY
    if side_value == "sell":
        return enums.OrderSide.SELL
    logger.warning("Unknown order side '%s', defaulting to BUY", side)
    return enums.OrderSide.BUY


def _map_order_status(status: str) -> str:
    status_value = (status or "").strip().lower()
    if status_value in {"complete", "completed", "filled"}:
        return enums.OrderStatus.COMPLETED.value
    if status_value in {"rejected", "cancelled", "failed"}:
        return enums.OrderStatus.FAILED.value
    return enums.OrderStatus.PENDING.value


def _coerce_price(primary, fallback) -> float:
    try:
        return float(primary)
    except (TypeError, ValueError):
        try:
            return float(fallback)
        except (TypeError, ValueError):
            return 0.0


