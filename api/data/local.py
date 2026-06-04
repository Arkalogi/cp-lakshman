from typing import Any, Dict, List, Optional, Tuple


MASTER_DATA = {}
TOKEN_MAP = {}
PRICE_CACHE: Dict[str, float] = {}
PREV_CLOSE_CACHE: Dict[str, float] = {}
# Pre-computed day change (absolute) and day change % per instrument
DAY_CHANGE_CACHE: Dict[str, float] = {}
DAY_CHANGE_PCT_CACHE: Dict[str, float] = {}
MASTER_DATA_SERIALIZED: Dict[str, Dict[str, Any]] = {}
MASTER_DATA_LIST: List[Dict[str, Any]] = []
UNDERLYING_INDEX: Dict[str, List[str]] = {}
XTS_TO_UPSTOX_KEY: Dict[str, str] = {}
UPSTOX_TO_XTS_ID: Dict[str, str] = {}
UPSTOX_TOKEN_BY_XTS_ID: Dict[str, str] = {}
# composite (exchange, underlying, instrument_type, expiry, strike, option_type) -> upstox instrument_key
# Kept alive after _refresh_xts_upstox_map so unmapped instruments can be looked up at runtime
UPSTOX_INSTRUMENT_BY_KEY: Dict[Tuple, str] = {}
