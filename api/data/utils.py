import asyncio
import json
import os
import logging
import requests
from datetime import datetime
from typing import Any, Iterable, List, Optional
from sqlalchemy import insert, select
from api.data.local import (
    MASTER_DATA,
    MASTER_DATA_LIST,
    MASTER_DATA_SERIALIZED,
    PRICE_CACHE,
    TOKEN_MAP,
    UNDERLYING_INDEX,
    XTS_TO_UPSTOX_KEY,
    UPSTOX_TO_XTS_ID,
    UPSTOX_TOKEN_BY_XTS_ID,
)
from api.data.models import Instrument
from api.data import models, database, red
from api.commons.constants import ZERODHA_MASTER_DATA_URL
from api.commons.enums import Exchange, InstrumentType, OptionType
from api.commons.utils import generate_trading_symbol
from api.config import Config

logger = logging.getLogger(__name__)


def _as_date_int_from_epoch_ms(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        ts_seconds = float(value) / 1000.0
    except (TypeError, ValueError):
        return None
    return datetime.utcfromtimestamp(ts_seconds).strftime("%Y%m%d")


def _normalize_instrument_type(value: Any) -> Optional[str]:
    raw = str(value or "").strip().upper()
    if raw in {"CE", "PE", "OPT"}:
        return "OPT"
    if raw in {"FUT", "FUTIDX", "FUTSTK"}:
        return "FUT"
    if raw in {"EQ", "EQUITY"}:
        return "EQ"
    return None


def _safe_float_str(value: Any) -> str:
    try:
        return f"{float(value):.6f}"
    except (TypeError, ValueError):
        return "0.000000"


def _build_upstox_match_key(row: dict[str, Any]) -> Optional[tuple]:
    exchange = str(row.get("exchange") or "").strip().upper()
    instrument_type = _normalize_instrument_type(row.get("instrument_type"))
    if not exchange or not instrument_type:
        return None
    underlying = str(
        row.get("underlying_symbol")
        or row.get("asset_symbol")
        or row.get("name")
        or row.get("trading_symbol")
        or ""
    ).strip().upper()
    if not underlying:
        return None
    option_type = str(row.get("instrument_type") or "").strip().upper()
    if option_type not in {"CE", "PE"}:
        option_type = ""
    expiry = _as_date_int_from_epoch_ms(row.get("expiry")) if instrument_type != "EQ" else ""
    strike = _safe_float_str(row.get("strike_price")) if instrument_type == "OPT" else "0.000000"
    return (exchange, underlying, instrument_type, expiry or "", strike, option_type)


def _build_xts_match_key(instrument: Instrument) -> Optional[tuple]:
    exchange = (instrument.exchange.name if instrument.exchange else "").replace("CM", "").replace("FO", "")
    exchange = exchange.strip().upper()
    instrument_type = (
        instrument.instrument_type.name.upper() if instrument.instrument_type else None
    )
    if not exchange or not instrument_type:
        return None
    underlying = str(instrument.underlying or "").strip().upper()
    if not underlying:
        return None
    option_type = (
        instrument.option_type.name.upper() if instrument.option_type else ""
    )
    expiry = str(instrument.expiry or "") if instrument_type != "EQ" else ""
    strike = _safe_float_str(instrument.strike) if instrument_type == "OPT" else "0.000000"
    return (exchange, underlying, instrument_type, expiry, strike, option_type)


def load_upstox_master_data_from_file() -> list[dict[str, Any]]:
    file_path = Config.UPSTOX_MASTER_DATA_FILE_PATH
    if not os.path.isabs(file_path):
        file_path = os.path.join(os.getcwd(), file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)
    with open(file_path, "r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, list):
        raise ValueError("Upstox master data must be a JSON array")
    return payload


def _refresh_xts_upstox_map(instruments: List[Instrument]) -> None:
    XTS_TO_UPSTOX_KEY.clear()
    UPSTOX_TO_XTS_ID.clear()
    UPSTOX_TOKEN_BY_XTS_ID.clear()

    try:
        upstox_rows = load_upstox_master_data_from_file()
    except FileNotFoundError:
        logger.warning(
            "Upstox master data file not found at %s; skipping XTS<->Upstox mapping.",
            Config.UPSTOX_MASTER_DATA_FILE_PATH,
        )
        return
    except Exception as exc:
        logger.exception("Failed to load Upstox master data for mapping: %s", exc)
        return

    upstox_by_key: dict[tuple, dict[str, Any]] = {}
    upstox_by_exchange_token: dict[tuple[str, str], dict[str, Any]] = {}
    for row in upstox_rows:
        if not isinstance(row, dict):
            continue
        exchange = str(row.get("exchange") or "").strip().upper()
        exchange_token = str(row.get("exchange_token") or "").strip()
        if exchange and exchange_token and (exchange, exchange_token) not in upstox_by_exchange_token:
            upstox_by_exchange_token[(exchange, exchange_token)] = row
        key = _build_upstox_match_key(row)
        instrument_key = str(row.get("instrument_key") or "").strip()
        if key is None or not instrument_key or key in upstox_by_key:
            continue
        upstox_by_key[key] = row

    mapped = 0
    for instrument in instruments:
        exchange = (instrument.exchange.name if instrument.exchange else "").replace("CM", "").replace("FO", "")
        exchange = exchange.strip().upper()
        xts_id = str(instrument.instrument_id)
        upstox = upstox_by_exchange_token.get((exchange, xts_id))
        if not upstox:
            xts_key = _build_xts_match_key(instrument)
            if xts_key is None:
                continue
            upstox = upstox_by_key.get(xts_key)
        if not upstox:
            continue
        upstox_key = str(upstox.get("instrument_key") or "").strip()
        upstox_token = str(upstox.get("exchange_token") or "").strip()
        if not upstox_key:
            continue
        XTS_TO_UPSTOX_KEY[xts_id] = upstox_key
        UPSTOX_TO_XTS_ID[upstox_key] = xts_id
        if upstox_token:
            UPSTOX_TOKEN_BY_XTS_ID[xts_id] = upstox_token
        mapped += 1

    logger.info(
        "XTS<->Upstox mapping ready: mapped=%d xts=%d upstox=%d",
        mapped,
        len(instruments),
        len(upstox_by_key),
    )


def download_zerodha_master_data():
    response = requests.get(ZERODHA_MASTER_DATA_URL)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(
            f"Error downloading Zerodha master data, Status Code: {response.status_code}, Response: {response.text}"
        )


def store_master_data(data: str):
    file_path = "zerodha_master_data.csv"
    with open(file_path, "w") as file:
        file.write(data)


def parse_zerodha_master_data(master_data: str): ...


def download_xts_master_data():
    XTS_MASTER_DATA_URL = Config.XTS_BASE_URL + "/apimarketdata/instruments/master"
    HEADERS = {
        "Content-Type": "application/json",
    }
    payload = {
        "exchangeSegmentList": ["NSEFO", "NSECM", "BSECM", "BSEFO"],
    }
    response = requests.post(XTS_MASTER_DATA_URL, headers=HEADERS, data=json.dumps(payload))
    print(f"XTS master data download response: {response.status_code}, {response.text[:200]}...")
    if response.status_code == 200:
        return response.json()["result"].strip()
    else:
        raise Exception(
            f"Error downloading XTS master data, Status Code: {response.status_code}, Response: {response.text}"
        )


def load_xts_master_data_from_file() -> str:
    file_path = Config.DATA_DIR + "/" + Config.XTS_MASTER_DATA_FILE_PATH
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)
    with open(file_path, "r") as file:
        data = file.read()
    return data


def store_xts_master_data(data: str):
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    file_path = Config.DATA_DIR + "/" + Config.XTS_MASTER_DATA_FILE_PATH
    with open(file_path, "w") as file:
        file.write(data)


def parser_xts_master_data(master_data: str) -> List[Instrument]:
    lines = master_data.split("\n")
    EXCHANGE_COLUMN = 0
    INSTRUMENT_ID_COLUMN = 1
    UNDERLYING_COLUMN = 3
    INSTRUMENT_TYPE_COLUMN = 5
    FREEZE_QTY_COLUMN = 10
    LOT_SIZE_COLUMN = 12
    EXPIRY_COLUMN = 16
    STRIKE_COLUMN = 17
    OPTION_TYPE_COLUMN = 18
    instruments: List[Instrument] = []
    for line in lines[1:]:
        if line.strip() == "":
            continue
        parts = line.split("|")
        exchange = parts[EXCHANGE_COLUMN].lower()
        if exchange not in Exchange._value2member_map_:
            continue
        exchange_enum = Exchange(exchange)
        instrument_type = parts[INSTRUMENT_TYPE_COLUMN]
        if instrument_type in ["OPTSTK", "OPTIDX"]:
            instrument_type_enum = InstrumentType.OPT
        elif instrument_type in ["FUTSTK", "FUTIDX"]:
            instrument_type_enum = InstrumentType.FUT
        elif instrument_type == "EQ":
            instrument_type_enum = InstrumentType.EQ
        else:
            continue
        instrument_id = parts[INSTRUMENT_ID_COLUMN]
        underlying = parts[UNDERLYING_COLUMN]
        lot_size = parts[LOT_SIZE_COLUMN]
        expiry = parts[EXPIRY_COLUMN]
        strike = parts[STRIKE_COLUMN]
        option_type = parts[OPTION_TYPE_COLUMN]
        expiry_date = expiry.split("T")[0] if instrument_type_enum != InstrumentType.EQ else None
        expiry_int = expiry_date.replace("-", "") if expiry_date else None
        option_type_enum = None
        if option_type == "3":
            option_type_enum = OptionType.CE
        elif option_type == "4":
            option_type_enum = OptionType.PE
        if instrument_type_enum == InstrumentType.OPT and option_type_enum is None:
            continue
        strike_price = 0.0
        if strike != "":
            try:
                strike_price = float(strike)
            except ValueError:
                strike_price = 0.0
        try:
            freeze_qty = int(parts[FREEZE_QTY_COLUMN]) - 1 if exchange_enum in [Exchange.NSEFO, Exchange.NSECM] else int(parts[FREEZE_QTY_COLUMN])
        except (ValueError, TypeError):
            freeze_qty = 0
        option_type_name = option_type_enum.name if option_type_enum else None
        instrument = Instrument(
            instrument_id=instrument_id,
            exchange=exchange_enum,
            trading_symbol=generate_trading_symbol(
                exchange=exchange_enum.name,
                underlying=underlying,
                instrument_type=instrument_type_enum.name,
                expiry=expiry_int,
                strike=strike_price,
                option_type=option_type_name,
            ),
            underlying=underlying,
            instrument_type=instrument_type_enum,
            lot_size=lot_size,
            freeze_quantity=freeze_qty,
            expiry=expiry_int,
            strike=strike_price,
            option_type=option_type_enum,
        )
        instruments.append(instrument)
    return instruments


def _chunked(items: Iterable[dict], size: int) -> Iterable[List[dict]]:
    batch: List[dict] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _serialize_instrument(instrument: Instrument) -> dict[str, Any]:
    xts_id = str(instrument.instrument_id)
    return {
        "instrument_id": xts_id,
        "exchange": instrument.exchange.value if instrument.exchange else None,
        "trading_symbol": instrument.trading_symbol,
        "underlying": instrument.underlying,
        "instrument_type": (
            instrument.instrument_type.value if instrument.instrument_type else None
        ),
        "lot_size": instrument.lot_size,
        "freeze_quantity": instrument.freeze_quantity,
        "expiry": instrument.expiry,
        "strike": instrument.strike,
        "option_type": instrument.option_type.value if instrument.option_type else None,
        "upstox_instrument_key": XTS_TO_UPSTOX_KEY.get(xts_id),
        "upstox_exchange_token": UPSTOX_TOKEN_BY_XTS_ID.get(xts_id),
    }


def _refresh_master_cache(instruments: List[Instrument]) -> None:
    MASTER_DATA.clear()
    TOKEN_MAP.clear()
    MASTER_DATA_SERIALIZED.clear()
    MASTER_DATA_LIST.clear()
    UNDERLYING_INDEX.clear()
    for instrument in instruments:
        MASTER_DATA[instrument.instrument_id] = instrument
        TOKEN_MAP[instrument.trading_symbol] = instrument.instrument_id
        serialized = _serialize_instrument(instrument)
        MASTER_DATA_SERIALIZED[instrument.instrument_id] = serialized
        MASTER_DATA_LIST.append(serialized)
        underlying_key = (serialized["underlying"] or "").upper()
        if underlying_key:
            UNDERLYING_INDEX.setdefault(underlying_key, []).append(
                instrument.instrument_id
            )


async def _persist_master_data(instruments: List[Instrument]) -> None:
    if not instruments:
        return
    rows = [
        {
            "instrument_id": instrument.instrument_id,
            "exchange": instrument.exchange,
            "trading_symbol": instrument.trading_symbol,
            "underlying": instrument.underlying,
            "instrument_type": instrument.instrument_type,
            "lot_size": instrument.lot_size,
            "freeze_quantity": instrument.freeze_quantity,
            "expiry": instrument.expiry,
            "strike": instrument.strike,
            "option_type": instrument.option_type,
        }
        for instrument in instruments
    ]
    async with database.DbAsyncSession() as db:
        for chunk in _chunked(rows, 1000):
            stmt = insert(models.Instrument).values(chunk).prefix_with("IGNORE")
            await db.execute(stmt)
        await db.commit()


async def _load_master_cache_from_db() -> bool:
    async with database.DbAsyncSession() as db:
        result = await db.execute(select(models.Instrument))
        instruments = result.scalars().all()
    if not instruments:
        return False
    _refresh_xts_upstox_map(instruments)
    _refresh_master_cache(instruments)
    return True


async def load_master_data() -> bool:
    try:
        if Config.DOWNLOAD_XTS_MASTER_DATA:
            xts_data = await asyncio.to_thread(download_xts_master_data)
            await asyncio.to_thread(store_xts_master_data, xts_data)
        else:
            try:
                xts_data = await asyncio.to_thread(load_xts_master_data_from_file)
            except FileNotFoundError as e:
                logger.warning(
                    "Master data file not found at %s. Falling back to database cache.",
                    str(e),
                )
                loaded = await _load_master_cache_from_db()
                if loaded:
                    logger.info(
                        "Master data loaded from database fallback: %d instruments",
                        len(MASTER_DATA),
                    )
                else:
                    logger.warning("Master data unavailable after load attempt.")
                return loaded
        instruments = await asyncio.to_thread(parser_xts_master_data, xts_data)
        await _persist_master_data(instruments)
        _refresh_xts_upstox_map(instruments)
        _refresh_master_cache(instruments)
        logger.info("Master data loaded from source: %d instruments", len(MASTER_DATA))
        return True
    except Exception as e:
        logger.exception("Error loading master data: %s", e)
        loaded = await _load_master_cache_from_db()
        if loaded:
            logger.info(
                "Master data loaded from database fallback: %d instruments",
                len(MASTER_DATA),
            )
        else:
            logger.warning("Master data unavailable after load attempt.")
        return loaded
    
def get_instrument_by_id(instrument_id: str) -> Optional[Instrument]:
    return MASTER_DATA.get(instrument_id)

def get_instrument_by_trading_symbol(trading_symbol: str) -> Optional[Instrument]:
    instrument_id = TOKEN_MAP.get(trading_symbol)
    if instrument_id:
        return MASTER_DATA.get(instrument_id)
    return None


def get_master_data_snapshot() -> List[dict[str, Any]]:
    return MASTER_DATA_LIST


def get_master_data_count() -> int:
    return len(MASTER_DATA_LIST)


def get_instrument_payload_by_id(instrument_id: str) -> Optional[dict[str, Any]]:
    return MASTER_DATA_SERIALIZED.get(instrument_id)


def get_upstox_instrument_key_by_xts_id(instrument_id: str) -> Optional[str]:
    return XTS_TO_UPSTOX_KEY.get(str(instrument_id))


def get_xts_instrument_id_by_upstox_key(instrument_key: str) -> Optional[str]:
    return UPSTOX_TO_XTS_ID.get(str(instrument_key))


def search_instruments(
    *,
    trading_symbol: Optional[str] = None,
    underlying: Optional[str] = None,
    exchange: Optional[str] = None,
    instrument_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    limit = max(1, min(limit, 1000))
    offset = max(0, offset)

    filtered_ids: Optional[set[str]] = None
    if underlying:
        filtered_ids = set(UNDERLYING_INDEX.get(underlying.upper(), []))

    if filtered_ids is not None:
        rows = [
            MASTER_DATA_SERIALIZED[instrument_id]
            for instrument_id in filtered_ids
            if instrument_id in MASTER_DATA_SERIALIZED
        ]
    else:
        rows = MASTER_DATA_LIST

    symbol_filter = trading_symbol.lower() if trading_symbol else None
    exchange_filter = exchange.lower() if exchange else None
    type_filter = instrument_type.lower() if instrument_type else None

    if symbol_filter or exchange_filter or type_filter:

        def _matches(item: dict[str, Any]) -> bool:
            if symbol_filter and symbol_filter not in (item["trading_symbol"] or "").lower():
                return False
            if exchange_filter and exchange_filter != (item["exchange"] or "").lower():
                return False
            if type_filter and type_filter != (item["instrument_type"] or "").lower():
                return False
            return True

        rows = [item for item in rows if _matches(item)]

    total = len(rows)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": rows[offset : offset + limit],
    }

async def get_current_price(instrument_id: str) -> Optional[float]:
    instrument_id = str(instrument_id)
    cached = PRICE_CACHE.get(instrument_id)
    if cached is not None:
        return cached
    return await red.get_live_price(instrument_id)
