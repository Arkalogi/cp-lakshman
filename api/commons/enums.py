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