import requests
from typing import List
from api.data.local import MASTER_DATA, TOKEN_MAP
from api.data.models import Instrument
from api.data import models, database
from api.commons.constants import ZERODHA_MASTER_DATA_URL
from api.commons.enums import Exchange, InstrumentType, OptionType
from api.commons.utils import generate_trading_symbol
from api.config import Config


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
        expiry_int = 0
        if expiry_date:
            expiry_int = expiry_date.replace("-", "") if instrument_type_enum != InstrumentType.EQ else None
        option_type_enum = None
        if option_type == "3":
            option_type_enum = OptionType.CE
        elif option_type == "4":
            option_type_enum = OptionType.PE
        strike_price = 0.0
        if strike != "":
            try:
                strike_price = float(strike)
            except ValueError:
                strike_price = 0.0
        instrument = Instrument(
            instrument_id=instrument_id,
            exchange=exchange_enum,
            trading_symbol=generate_trading_symbol(
                exchange=exchange_enum.value,
                underlying=underlying,
                instrument_type=instrument_type_enum.value,
                expiry=expiry_int,
                strike=strike_price,
                option_type=option_type_enum.value,
            ),
            underlying=underlying,
            instrument_type=instrument_type_enum,
            lot_size=lot_size,
            freeze_quantity=int(parts[FREEZE_QTY_COLUMN]),
            expiry=expiry_int,
            strike=strike_price,
            option_type=option_type_enum,
        )


def load_master_data():
    try:
        if Config.DOWNLOAD_XTS_MASTER_DATA:
            xts_data = download_xts_master_data()
            store_xts_master_data(xts_data)
        else:
            xts_data = load_xts_master_data_from_file()
        parser_xts_master_data(xts_data)
    except Exception as e:
        print(f"Error downloading Zerodha master data: {e}")
        return


def make_token_map(): ...
