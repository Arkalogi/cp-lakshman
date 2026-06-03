import os
import redis
import redis.asyncio as redis_async

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_REDIS_SOCKET_CONNECT_TIMEOUT = float(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))
_REDIS_SOCKET_TIMEOUT_VALUE = os.getenv("REDIS_SOCKET_TIMEOUT", "")
ORDER_SIGNAL_LIST = os.getenv("ORDER_SIGNAL_LIST", "order_signals")
ORDER_ROUTER_LIST = os.getenv("ORDER_ROUTER_LIST", "order_router")
LIVE_PRICE_HASH = os.getenv("LIVE_PRICE_HASH", "live_prices")
LIVE_PRICE_PREV_CLOSE_HASH = os.getenv("LIVE_PRICE_PREV_CLOSE_HASH", "live_prices_prev_close")

_redis_sync = None
_redis_async = None


def _socket_timeout() -> float | None:
    if not _REDIS_SOCKET_TIMEOUT_VALUE:
        return None
    if _REDIS_SOCKET_TIMEOUT_VALUE.strip().lower() in {"none", "null"}:
        return None
    return float(_REDIS_SOCKET_TIMEOUT_VALUE)


def _redis_options() -> dict:
    return {
        "decode_responses": False,
        "socket_connect_timeout": _REDIS_SOCKET_CONNECT_TIMEOUT,
        "socket_timeout": _socket_timeout(),
        "health_check_interval": 30,
    }


def get_redis():
    global _redis_sync
    if _redis_sync is None:
        _redis_sync = redis.Redis.from_url(_REDIS_URL, **_redis_options())
    return _redis_sync


def get_async_redis():
    global _redis_async
    if _redis_async is None:
        _redis_async = redis_async.from_url(_REDIS_URL, **_redis_options())
    return _redis_async


def _encode(value: str | float) -> bytes:
    return str(value).encode("utf-8")


async def set_live_price(
    instrument_id: str,
    price: float,
    *,
    previous_close: float | None = None,
) -> None:
    redis_client = get_async_redis()
    await redis_client.hset(LIVE_PRICE_HASH, _encode(instrument_id), _encode(price))
    if previous_close is not None:
        await redis_client.hset(
            LIVE_PRICE_PREV_CLOSE_HASH,
            _encode(instrument_id),
            _encode(previous_close),
        )


async def get_live_price(instrument_id: str) -> float | None:
    raw_value = await get_async_redis().hget(LIVE_PRICE_HASH, _encode(instrument_id))
    if raw_value is None:
        return None
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return None
