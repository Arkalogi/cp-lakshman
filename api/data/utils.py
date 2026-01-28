import asyncio
import os
import logging
import requests
from typing import Iterable, List
from sqlalchemy import insert, select
from api.data.local import MASTER_DATA, TOKEN_MAP
from api.data.models import Instrument
from api.data import models, database
from api.commons.constants import ZERODHA_MASTER_DATA_URL
from api.commons.enums import Exchange, InstrumentType, OptionType
from api.commons.utils import generate_trading_symbol
from api.config import Config

logger = logging.getLogger(__name__)


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
        "exchangeSegmentList": ["NSEFO", "NSECM", "BSECM", "NSECD"],
    }
    response = requests.get(XTS_MASTER_DATA_URL, headers=HEADERS, data=payload)
    if response.status_code == 200:
        return response.json()["result"].strip()
    else:
        raise Exception(
            f"Error downloading XTS master data, Status Code: {response.status_code}, Response: {response.text}"
        )


def load_xts_master_data_from_file() -> str:
    file_path = Config.DATA_DIR + "/" + Config.XTS_MASTER_DATA_FILE_PATH
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
    EXCHANGE_INDEX = 0
    INSTRUMENT_ID_INDEX = 1
    UNDERLYING_INDEX = 3
    INSTRUMENT_TYPE_INDEX = 5
    FREEZE_QTY_COLUMN = 10
    LOT_SIZE_INDEX = 12
    EXPIRY_INDEX = 16
    STRIKE_INDEX = 17
    OPTION_TYPE_INDEX = 18
    instruments: List[Instrument] = []
    for line in lines[1:]:
        if line.strip() == "":
            continue
        parts = line.split("|")
        exchange = parts[EXCHANGE_INDEX]
        if exchange not in Exchange._value2member_map_:
            continue
        exchange_enum = Exchange(exchange)
        instrument_type = parts[INSTRUMENT_TYPE_INDEX]
        if instrument_type in ["OPTSTK", "OPTIDX"]:
            instrument_type_enum = InstrumentType.OPT
        elif instrument_type in ["FUTSTK", "FUTIDX"]:
            instrument_type_enum = InstrumentType.FUT
        elif instrument_type == "EQ":
            instrument_type_enum = InstrumentType.EQ
        else:
            continue
        instrument_id = parts[INSTRUMENT_ID_INDEX]
        underlying = parts[UNDERLYING_INDEX]
        lot_size = parts[LOT_SIZE_INDEX]
        expiry = parts[EXPIRY_INDEX]
        strike = parts[STRIKE_INDEX]
        option_type = parts[OPTION_TYPE_INDEX]
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
            freeze_qty = int(parts[FREEZE_QTY_COLUMN])
        except (ValueError, TypeError):
            freeze_qty = 0
        option_type_value = option_type_enum.value if option_type_enum else None
        instrument = Instrument(
            instrument_id=instrument_id,
            exchange=exchange_enum,
            trading_symbol=generate_trading_symbol(
                exchange=exchange_enum.value,
                underlying=underlying,
                instrument_type=instrument_type_enum.value,
                expiry=expiry_int,
                strike=strike_price,
                option_type=option_type_value,
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


def _refresh_master_cache(instruments: List[Instrument]) -> None:
    MASTER_DATA.clear()
    TOKEN_MAP.clear()
    for instrument in instruments:
        MASTER_DATA[instrument.instrument_id] = instrument
        TOKEN_MAP[instrument.trading_symbol] = instrument.instrument_id


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
    _refresh_master_cache(instruments)
    return True


async def load_master_data():
    try:
        if Config.DOWNLOAD_XTS_MASTER_DATA:
            xts_data = await asyncio.to_thread(download_xts_master_data)
            await asyncio.to_thread(store_xts_master_data, xts_data)
        else:
            xts_data = await asyncio.to_thread(load_xts_master_data_from_file)
        instruments = await asyncio.to_thread(parser_xts_master_data, xts_data)
        await _persist_master_data(instruments)
        _refresh_master_cache(instruments)
    except Exception as e:
        logger.exception("Error loading master data: %s", e)
        await _load_master_cache_from_db()
        return

