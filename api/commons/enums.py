from enum import Enum

class ResponseStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    

class ApiProvider(Enum):
    UPSTOX = "upstox"
    KITE = "kite"
    SHOONYA = "shoonya"


class DematProvider(Enum):
    ZERODHA = "zerodha"
    FINVASIA = "finvasia"