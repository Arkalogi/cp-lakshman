import asyncio
import requests
import pyotp
import base64
from uvicorn import Config
import websocket
import logging
from typing import Dict
from api.commons import enums
from api.data import red
from urllib.parse import urlencode, urlparse, parse_qs

from api.data import database, upstox_feed_parser, upstox_json_format
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

    async def start_order_update_socket(self, livefeed_token: str, livefeed_refresh_token: str):
        self._loop = asyncio.get_running_loop()
        ws = websocket.WebSocketApp(
            "wss://api.upstox.com/v3/feed/market-data-feed",
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            cookie=f"access_token={livefeed_token};refresh_token={livefeed_refresh_token}",
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
        if self.backfilling:
            return
        message = upstox_feed_parser.FeedResponse.FromString(message)
        message = upstox_json_format.MessageToDict(message)
        if "feeds" not in message:
            return
        for token, token_message in message["feeds"].items():
            if token not in self.subscribed_tokens:
                continue
            ff_json = token_message["fullFeed"]
            market_ff_json = ff_json.get("marketFF", ff_json.get("indexFF"))
            market_ohlc_json = market_ff_json["marketOHLC"]
            ohlcs_json = market_ohlc_json["ohlc"]

            i1_ohlcs_json = [
                ohlc_json
                for ohlc_json in ohlcs_json
                if ohlc_json.get("interval") == "I1"
            ]
            if len(i1_ohlcs_json) < 1:
                continue
            latest_i1_ohlc_json = i1_ohlcs_json[-1]

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


