import asyncio
import requests
import pyotp
import base64
import websocket
import logging
import json
from typing import Dict
from api.config import Config
from urllib.parse import urlencode, urlparse, parse_qs

logger = logging.getLogger(__name__)

UPSTOX_BASE_URL = "https://api.upstox.com/v2"
UPSTOX_SERVICE_URL = "https://service.upstox.com"

quantity_processed: Dict[str, int] = {}


async def login(api_config: dict):
    api_key = api_config["api_key"]
    api_secret = api_config["api_secret"]
    redirect_url = api_config["redirect_url"]
    mobile_number = api_config["mobile_number"]
    totp_secret = api_config["totp_secret"]
    pin: str = api_config["pin"]
    livefeed_token = None
    livefeed_refresh_token = None
    with requests.Session() as session:
        url = UPSTOX_BASE_URL + "/login/authorization/dialog"

        url = (
            UPSTOX_BASE_URL
            + "/login/authorization/dialog"
            + f"?{urlencode({
                "client_id": api_key,
                "redirect_uri": redirect_url,
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
        payload = {"data": {"mobileNumber": mobile_number, "userId": user_id}}
        response = session.post(url, json=payload)
        validate_otp_token = response.json()["data"]["validateOTPToken"]
        totp = pyotp.TOTP(totp_secret)
        url = UPSTOX_SERVICE_URL + "/login/open/v4/auth/1fa/otp-totp/verify"
        payload = {"data": {"otp": totp.now(), "validateOtpToken": validate_otp_token}}
        response = session.post(url, json=payload, allow_redirects=False)

        encoded_pin = base64.b64encode(pin.encode("utf-8")).decode("utf-8")
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
            "client_id": api_key,
            "client_secret": api_secret,
            "redirect_uri": redirect_url,
            "grant_type": "authorization_code",
        }
        response = requests.post(url, data=payload, headers=headers)
        access_token = response.json()["access_token"]

    return livefeed_token, livefeed_refresh_token, access_token


def on_open(_):
    logger.info("Order update socket is connected.")


def on_message(_, message: dict):
    # logger.info(f"Message: {message}")
    message_json = json.loads(message)
    update_type = message_json["update_type"]
    if update_type == "order":
        status = message_json["status"]
        user_id = message_json["user_id"]
        order_id = message_json["order_id"]
        side = message_json["transaction_type"]
        average_price = message_json["average_price"]
        filled_quantity = message_json["filled_quantity"]
        logger.info(f"Order(id: {order_id}, user_id: {user_id}, status: {status}, side: {side}, average_price: {average_price}, filled_quantity: {filled_quantity})")


def on_error(_, error_code: str, message: dict):
    logger.info(f"Order update error: {error_code}::{message}")


def on_close(_, message: dict):
    logger.info(f"Order update socket is closed")


async def start(api_config: dict):
    reconnect_delay = 2
    max_reconnect_delay = 30
    try:
        _, _, access_token = await login(api_config)
        headers = {"Authorization": f"Bearer {access_token}"}
        ws = websocket.WebSocketApp(
            "wss://api.upstox.com/v2/feed/portfolio-stream-feed?update_types=order",
            header=headers,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        ws.run_forever(reconnect=5)
    except:
        logger.exception(f"Order update login failed")
