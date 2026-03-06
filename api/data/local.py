from typing import Any, Dict, List


MASTER_DATA = {}
TOKEN_MAP = {}
PRICE_CACHE: Dict[str, float] = {}
PREV_CLOSE_CACHE: Dict[str, float] = {}
MASTER_DATA_SERIALIZED: Dict[str, Dict[str, Any]] = {}
MASTER_DATA_LIST: List[Dict[str, Any]] = []
UNDERLYING_INDEX: Dict[str, List[str]] = {}
XTS_TO_UPSTOX_KEY: Dict[str, str] = {}
UPSTOX_TO_XTS_ID: Dict[str, str] = {}
UPSTOX_TOKEN_BY_XTS_ID: Dict[str, str] = {}
