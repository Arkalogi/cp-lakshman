import os
import redis
import redis.asyncio as redis_async

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ORDER_SIGNAL_LIST = os.getenv("ORDER_SIGNAL_LIST", "order_signals")
ORDER_ROUTER_LIST = os.getenv("ORDER_ROUTER_LIST", "order_router")

_redis_sync = None
_redis_async = None


def get_redis():
    global _redis_sync
    if _redis_sync is None:
        _redis_sync = redis.Redis.from_url(_REDIS_URL, decode_responses=False)
    return _redis_sync


def get_async_redis():
    global _redis_async
    if _redis_async is None:
        _redis_async = redis_async.from_url(_REDIS_URL, decode_responses=False)
    return _redis_async