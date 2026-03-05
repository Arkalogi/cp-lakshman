import logging
import pyotp
import base64
import requests
import json
from urllib.parse import urlparse, parse_qs, urlencode

import websocket
from utils import upstox_feed_parser, upstox_json_format

logger = logging.getLogger(__name__)

UPSTOX_BASE_URL = "https://api.upstox.com/v2"
UPSTOX_SERVICE_URL = "https://service.upstox.com"


class UpstoxProvider:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        redirect_url: str,
        mobile_number: str,
        totp_secret: str,
        pin: str,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_url = redirect_url
        self.mobile_number = mobile_number
        self.totp_secret = totp_secret
        self.pin = pin
        self.access_token = None
        self.refresh_token = None
        self.logged_in = False

    def login(self):
        with requests.Session() as session:
            url = (
                UPSTOX_BASE_URL
                + "/login/authorization/dialog"
                + f"?{urlencode({
                    "client_id": self.api_key,
                    "redirect_uri": "http://localhost",
                    "response_type": "code",
                    "scope": "general",
                    "state": "123",
                })}"
            )

            response = session.get(url=url, allow_redirects=False)
            user_id = parse_qs(urlparse(response.headers["location"]).query)["user_id"][
                0
            ]
            client_id = parse_qs(urlparse(response.headers["location"]).query)[
                "client_id"
            ][0]
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
            payload = {
                "data": {"otp": totp.now(), "validateOtpToken": validate_otp_token}
            }
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
                    self.access_token = cookie.value
                if "refresh_token" in cookie.name:
                    self.refresh_token = cookie.value

            url = (
                UPSTOX_SERVICE_URL
                + f"/login/v2/oauth/authorize?client_id={client_id}&redirect_uri=https%3A%2F%2Fapi-v2.upstox.com%2Flogin%2Fauthorization%2Fredirect&response_type=code"
            )
            payload = {"data": {"userOAuthApproval": True}}
            response = session.post(url, json=payload)
            code = parse_qs(urlparse(response.json()["data"]["redirectUri"]).query)[
                "code"
            ][0]
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
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            self.logged_in = True
            logger.info("Login successful.")
            return self.access_token

    def start(self, block: bool = True):
        if not self.logged_in or not self.access_token:
            self.login()
        headers = {
            "accept": "application/json",
            "Api-Version": "2.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {self.access_token}",
        }
        self.ws = websocket.WebSocketApp(
            "wss://api.upstox.com/v3/feed/market-data-feed",
            header=headers,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        if block:
            self.ws.run_forever(ping_interval=20, ping_timeout=10)
        return self.ws

    def subscribe_to_tokens(self, tokens: list):
        self.subscribed_tokens.update(tokens)
        try:
            payload = {
                "guid": "536e6b23-d527-4b30-b1a6-5bb024b3b591",
                "method": "sub",
                "data": {"instrumentKeys": self.subscribed_tokens, "mode": "full"},
            }
            logger.info(payload)
            self.ws.send(json.dumps(payload).encode(), opcode=2)
        except Exception as e:
            logger.exception("Feed subscription failed")

    def unsubscribe_from_tokens(self, tokens: list):
        self.subscribed_tokens.difference_update(tokens)
        try:
            payload = {
                "guid": "536e6b23-d527-4b30-b1a6-5bb024b3b591",
                "method": "unsub",
                "data": {"instrumentKeys": tokens, "mode": "full"},
            }
            logger.info(payload)
            self.ws.send(json.dumps(payload).encode(), opcode=2)
        except Exception as e:
            logger.exception("Feed unsubscription failed")

    def on_error(self, ws, error):
        logger.error(f"Websocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        logger.info(
            f"Websocket closed with code: {close_status_code}, message: {close_msg}"
        )

    def on_open(self, ws):
        logger.info("Websocket connection opened.")
        self.subscribe_to_tokens(["NSE_INDEX|Nifty 50"])

    def _decode_feed_message(self, message):
        if isinstance(message, (bytes, bytearray)):
            proto_message = upstox_feed_parser.FeedResponse.FromString(message)
            return upstox_json_format.MessageToDict(proto_message)
        if isinstance(message, str):
            try:
                return json.loads(message)
            except json.JSONDecodeError:
                return {"raw": message}
        return {"raw": str(message)}

    def on_message(self, ws, message):
        try:
            payload = self._decode_feed_message(message)
        except Exception:
            logger.exception("Failed to parse websocket payload")
            return

        feeds = payload.get("feeds") if isinstance(payload, dict) else None
        if not feeds:
            logger.info("Control message: %s", payload)
            return

        for instrument_key, feed_value in feeds.items():
            ltpc = None
            if isinstance(feed_value, dict):
                ltpc = feed_value.get("ltpc")
                if not ltpc:
                    full_feed = feed_value.get("fullFeed", {})
                    market_feed = (
                        full_feed.get("marketFF") or full_feed.get("indexFF") or {}
                    )
                    ltpc = market_feed.get("ltpc")
                if not ltpc:
                    ltpc = feed_value.get("firstLevelWithGreeks", {}).get("ltpc")

            if ltpc:
                logger.info(
                    "Tick %s ltp=%s ltt=%s cp=%s",
                    instrument_key,
                    ltpc.get("ltp"),
                    ltpc.get("ltt"),
                    ltpc.get("cp"),
                )
            else:
                logger.debug("Parsed feed for %s: %s", instrument_key, feed_value)
