import logging
import pyotp
import base64
import requests
import json
import threading
import time
from urllib.parse import urlparse, parse_qs, urlencode

import websocket
from utils import upstox_feed_parser, upstox_json_format

logger = logging.getLogger(__name__)

UPSTOX_BASE_URL = "https://api.upstox.com/v2"
UPSTOX_API_ROOT = "https://api.upstox.com"
UPSTOX_SERVICE_URL = "https://service.upstox.com"
DEFAULT_INDEX_SUBSCRIPTIONS = {"NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank"}
RETRY_BASE_SECONDS = 2
RETRY_MAX_SECONDS = 30
LOGIN_RETRY_ATTEMPTS = 3


class UpstoxProvider:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        redirect_url: str,
        mobile_number: str,
        totp_secret: str,
        pin: str,
        api_ws_url: str,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_url = redirect_url
        self.mobile_number = mobile_number
        self.totp_secret = totp_secret
        self.pin = pin
        self.api_ws_url = api_ws_url
        self.access_token = None
        self.refresh_token = None
        self.logged_in = False
        self.subscribed_tokens = set(DEFAULT_INDEX_SUBSCRIPTIONS)
        self.api_ws = None
        self._tokens_lock = threading.Lock()
        self._api_ws_listener_thread = None
        self._retry_attempt = 0

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

            response = session.get(url=url, allow_redirects=False, timeout=15)
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
            response = session.post(url, json=payload, timeout=15)
            validate_otp_token = response.json()["data"]["validateOTPToken"]
            totp = pyotp.TOTP(self.totp_secret)
            url = UPSTOX_SERVICE_URL + "/login/open/v4/auth/1fa/otp-totp/verify"
            payload = {
                "data": {"otp": totp.now(), "validateOtpToken": validate_otp_token}
            }
            response = session.post(url, json=payload, allow_redirects=False, timeout=15)

            encoded_pin = base64.b64encode(self.pin.encode("utf-8")).decode("utf-8")
            url = (
                UPSTOX_SERVICE_URL
                + f"/login/open/v3/auth/2fa?client_id={client_id}&redirect_uri=https%3A%2F%2Fapi-v2.upstox.com%2Flogin%2Fauthorization%2Fredirect"
            )
            payload = {"data": {"twoFAMethod": "SECRET_PIN", "inputText": encoded_pin}}
            response = session.post(url, json=payload, timeout=15)

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
            response = session.post(url, json=payload, timeout=15)
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
            response = requests.post(url, data=payload, headers=headers, timeout=15)
            response.raise_for_status()
            token_payload = response.json()
            self.access_token = token_payload.get("access_token") or self.access_token
            self.refresh_token = token_payload.get("refresh_token") or self.refresh_token
            if not self.access_token:
                raise RuntimeError("Login completed but access_token is missing.")
            self.logged_in = True
            logger.info("Login successful.")
            return self.access_token

    def start(self, block: bool = True):
        if not block:
            self._connect_market_ws_once(run_forever=False)
            return self.ws

        while True:
            try:
                self._connect_market_ws_once()
                self._retry_attempt = 0
                time.sleep(1)
            except Exception:
                delay = min(RETRY_MAX_SECONDS, RETRY_BASE_SECONDS * (2 ** self._retry_attempt))
                self._retry_attempt = min(self._retry_attempt + 1, 10)
                logger.exception(
                    "Market data websocket setup failed; retrying in %ss.",
                    delay,
                )
                time.sleep(delay)

    def _connect_market_ws_once(self, run_forever: bool = True):
        self._ensure_logged_in()

        self.ws = websocket.WebSocketApp(
            "wss://market-data.upstox.com/market-data-feeder/v2/feeds",
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            cookie=f"access_token={self.access_token};refresh_token={self.refresh_token}",
        )
        if run_forever:
            self.ws.run_forever(ping_interval=20, ping_timeout=10)
            logger.warning("Market data websocket disconnected; reconnecting.")

    def _ensure_logged_in(self):
        if self.logged_in and self.access_token:
            return
        for attempt in range(1, LOGIN_RETRY_ATTEMPTS + 1):
            try:
                self.login()
                return
            except Exception:
                if attempt >= LOGIN_RETRY_ATTEMPTS:
                    raise
                delay = min(RETRY_MAX_SECONDS, RETRY_BASE_SECONDS * attempt)
                logger.exception("Login failed (attempt %s). Retrying in %ss.", attempt, delay)
                time.sleep(delay)

    def _invalidate_auth(self):
        self.logged_in = False
        self.access_token = None
        self.refresh_token = None

    @staticmethod
    def _is_auth_error(error: object) -> bool:
        message = str(error or "").lower()
        return "403" in message or "401" in message or "forbidden" in message or "unauthorized" in message

    def _get_market_data_feed_ws_url(self) -> str:
        if not self.access_token:
            self.login()
        url = "wss://market-data.upstox.com/market-data-feeder/v2/feeds"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Api-Version": "2.0",
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code in (401, 403):
            logger.warning("Authorize rejected (%s). Re-authenticating.", response.status_code)
            self.login()
            headers["Authorization"] = f"Bearer {self.access_token}"
            response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        payload = response.json().get("data", {})
        ws_url = payload.get("authorized_redirect_uri") or payload.get("authorizedRedirectUri")
        if not ws_url:
            raise RuntimeError("Upstox authorize response missing redirect URI")
        return ws_url

    def _connect_api_ws(self):
        if not self.api_ws_url:
            return
        if self.api_ws and self.api_ws.connected:
            return
        self.api_ws = websocket.create_connection(self.api_ws_url, timeout=5)
        # API WS can stay idle for long periods; avoid treating idle recv as failure.
        self.api_ws.settimeout(30)
        self.api_ws.send(
            json.dumps({"action": "register_feed", "source": "upstox_pricefeed"})
        )
        self._start_api_ws_listener()

    def _start_api_ws_listener(self):
        if (
            self._api_ws_listener_thread
            and self._api_ws_listener_thread.is_alive()
        ):
            return
        self._api_ws_listener_thread = threading.Thread(
            target=self._api_ws_listener_loop,
            name="upstox-api-ws-listener",
            daemon=True,
        )
        self._api_ws_listener_thread.start()

    def _api_ws_listener_loop(self):
        while self.api_ws and self.api_ws.connected:
            try:
                raw = self.api_ws.recv()
            except websocket.WebSocketTimeoutException:
                # No control message from API WS within timeout window: keep listening.
                continue
            except websocket.WebSocketConnectionClosedException:
                logger.warning("API websocket listener detected closed connection.")
                self.api_ws = None
                break
            except Exception:
                logger.exception("API websocket listener error")
                self.api_ws = None
                break
            if not raw:
                continue
            try:
                message = json.loads(raw)
            except Exception:
                logger.debug("Ignoring non-JSON API websocket payload: %s", raw)
                continue
            msg_type = str(message.get("type", "")).strip().lower()
            action = str(message.get("action", "")).strip().lower()
            if msg_type == "feed_subscription_sync":
                tokens = [
                    str(token)
                    for token in (message.get("instrument_ids") or [])
                    if token is not None
                ]
                self._apply_subscription_sync(tokens)
                continue
            if action == "subscribe":
                tokens = [
                    str(token)
                    for token in (message.get("instrument_ids") or [])
                    if token is not None
                ]
                self.subscribe_to_tokens(tokens)
                continue
            if action == "unsubscribe":
                tokens = [
                    str(token)
                    for token in (message.get("instrument_ids") or [])
                    if token is not None
                ]
                self.unsubscribe_from_tokens(tokens)
                continue

    def _apply_subscription_sync(self, tokens: list[str]):
        target = {token for token in tokens if token}
        target.update(DEFAULT_INDEX_SUBSCRIPTIONS)
        with self._tokens_lock:
            current = set(self.subscribed_tokens)
        to_subscribe = sorted(target - current)
        to_unsubscribe = sorted(current - target)
        if to_subscribe:
            self.subscribe_to_tokens(to_subscribe)
        if to_unsubscribe:
            self.unsubscribe_from_tokens(to_unsubscribe)

    def subscribe_to_tokens(self, tokens: list):
        with self._tokens_lock:
            self.subscribed_tokens.update(tokens)
            instrument_keys = list(self.subscribed_tokens)
        try:
            payload = {
                "guid": "536e6b23-d527-4b30-b1a6-5bb024b3b591",
                "method": "sub",
                "data": {"instrumentKeys": instrument_keys, "mode": "full"},
            }
            logger.info(payload)
            self.ws.send(json.dumps(payload).encode(), opcode=2)
        except Exception as e:
            logger.exception("Feed subscription failed")

    def unsubscribe_from_tokens(self, tokens: list):
        safe_tokens = [token for token in tokens if token not in DEFAULT_INDEX_SUBSCRIPTIONS]
        if not safe_tokens:
            return
        with self._tokens_lock:
            self.subscribed_tokens.difference_update(safe_tokens)
        try:
            payload = {
                "guid": "536e6b23-d527-4b30-b1a6-5bb024b3b591",
                "method": "unsub",
                "data": {"instrumentKeys": safe_tokens, "mode": "full"},
            }
            logger.info(payload)
            self.ws.send(json.dumps(payload).encode(), opcode=2)
        except Exception as e:
            logger.exception("Feed unsubscription failed")

    def on_error(self, ws, error):
        logger.error(f"Websocket error: {error}")
        if self._is_auth_error(error):
            logger.warning("Authentication failure detected on websocket; resetting auth.")
            self._invalidate_auth()

    def on_close(self, ws, close_status_code, close_msg):
        logger.info(
            f"Websocket closed with code: {close_status_code}, message: {close_msg}"
        )
        if close_status_code in (1008, 1011):
            self._invalidate_auth()
        try:
            if self.api_ws:
                self.api_ws.close()
        except Exception:
            logger.debug("Failed to close API websocket cleanly.")
        self.api_ws = None
        self._api_ws_listener_thread = None

    def on_open(self, ws):
        logger.info("Websocket connection opened.")
        self.subscribe_to_tokens(list(DEFAULT_INDEX_SUBSCRIPTIONS))
        try:
            self._connect_api_ws()
        except Exception:
            logger.exception("Failed to connect API websocket publisher.")

    def _decode_feed_message(self, message):
        if isinstance(message, (bytes, bytearray)):
            proto_message = upstox_feed_parser.FeedResponse.FromString(message)
            # including_default_value_fields=True ensures cp=0.0 is NOT silently
            # dropped by MessageToDict. Without this, a zero previous-close is
            # indistinguishable from a missing one, which breaks day-change maths.
            # always_print_fields_with_no_presence=True ensures cp=0.0 is NOT
            # silently dropped. This is the upstox_json_format equivalent of the
            # standard protobuf library's including_default_value_fields=True.
            return upstox_json_format.MessageToDict(
                proto_message,
                always_print_fields_with_no_presence=True,
                preserving_proto_field_name=False,  # keep camelCase (fullFeed, marketFF …)
            )
        if isinstance(message, str):
            try:
                return json.loads(message)
            except json.JSONDecodeError:
                return {"raw": message}
        return {"raw": str(message)}

    @staticmethod
    def _extract_ltpc(feed_value: dict):
        """
        Walk every known nesting path and return the first LTPC dict that
        contains a nonzero ltp, plus the parent market-feed dict for OHLC.
        Returns (ltpc_dict | None, market_feed_dict).
        """
        if not isinstance(feed_value, dict):
            return None, {}

        # Path 1 – top-level ltpc  (LTPC-only mode)
        ltpc = feed_value.get("ltpc") or {}
        if ltpc.get("ltp"):
            return ltpc, {}

        # Path 2 – fullFeed → marketFF (equities) or indexFF (indices)
        full_feed   = feed_value.get("fullFeed") or {}
        market_feed = full_feed.get("marketFF") or full_feed.get("indexFF") or {}
        ltpc = market_feed.get("ltpc") or {}
        if ltpc.get("ltp"):
            return ltpc, market_feed

        # Path 3 – firstLevelWithGreeks (options)
        ltpc = (feed_value.get("firstLevelWithGreeks") or {}).get("ltpc") or {}
        if ltpc.get("ltp"):
            return ltpc, {}

        return None, {}

    @staticmethod
    def _extract_ohlc(market_feed: dict) -> dict:
        """
        Extract the daily (1d) OHLC candle from marketOHLC if present.
        Returns a dict with keys open, high, low, close, vol (all floats or None).
        """
        ohlc_list = (market_feed.get("marketOHLC") or {}).get("ohlc") or []
        for entry in ohlc_list:
            if isinstance(entry, dict) and entry.get("interval") == "1d":
                return {
                    "open":  entry.get("open"),
                    "high":  entry.get("high"),
                    "low":   entry.get("low"),
                    "close": entry.get("close"),
                    "vol":   entry.get("vol"),
                }
        return {}

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
            ltpc, market_feed = self._extract_ltpc(feed_value)
            if not ltpc:
                logger.debug("No LTPC for %s", instrument_key)
                continue

            ltp = ltpc.get("ltp")   # current price
            cp  = ltpc.get("cp")    # previous close (Upstox field name: cp)
            ltt = ltpc.get("ltt")   # last traded time (epoch ms)

            # cp can be 0.0 for newly listed / suspended instruments — treat as missing
            previous_close = cp if (cp and cp != 0) else None

            # Calculate day change in the pricefeed so every downstream consumer
            # (hub cache, WebSocket clients) gets authoritative values.
            day_change     = None
            day_change_pct = None
            if ltp and previous_close:
                day_change     = round(ltp - previous_close, 4)
                day_change_pct = round((ltp - previous_close) / previous_close * 100, 4)

            # Parse daily OHLC (open/high/low/vol) for richer market context
            ohlc = self._extract_ohlc(market_feed)

            publish_payload = {
                "action":         "publish",
                "instrument_id":  instrument_key,
                "price":          ltp,
                "previous_close": previous_close,
                "day_change":     day_change,
                "day_change_pct": day_change_pct,
                "open":           ohlc.get("open"),
                "high":           ohlc.get("high"),
                "low":            ohlc.get("low"),
                "volume":         ohlc.get("vol"),
                "ts":             ltt,
                "source":         "upstox",
            }

            try:
                self._connect_api_ws()
                if self.api_ws and self.api_ws.connected:
                    self.api_ws.send(json.dumps(publish_payload))
            except Exception:
                logger.exception(
                    "Failed to publish tick for %s to API websocket", instrument_key
                )
                self.api_ws = None

            logger.info(
                "Tick %s ltp=%s cp=%s chg=%s (%.4f%%) ts=%s",
                instrument_key, ltp, previous_close,
                day_change, day_change_pct or 0.0, ltt,
            )
