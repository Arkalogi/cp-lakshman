from enum import Enum


class ResponseStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"


class ApiProvider(Enum):
    UPSTOX = "upstox"
    KITE = "kite"
    SHOONYA = "shoonya"


class DematProvider(Enum):
    UPSTOX = "upstox"
    ZERODHA = "zerodha"
    FINVASIA = "finvasia"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class InstrumentType(Enum):
    EQ = "eq"
    FUT = "fut"
    OPT = "opt"


class Exchange(Enum):
    NSECM = "nsecm"
    NSEFO = "nsefo"
    BSECM = "bsecm"
    BSEFO = "bsefo"


class OptionType(Enum):
    CE = "ce"
    PE = "pe"