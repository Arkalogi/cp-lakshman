import os


class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "mysql+aiomysql://root:admin@localhost:3306/copy_db")
    EXTERNAL_REQUEST_TIMEOUT = int(os.getenv("EXTERNAL_REQUEST_TIMEOUT", "10"))
    DATA_DIR = os.getenv("DATA_DIR", "data")
    DOWNLOAD_KITE_MASTER_DATA = os.getenv("DOWNLOAD_KITE_MASTER_DATA", "True").lower() == "true"
    KITE_BASE_URL = os.getenv("KITE_BASE_URL", "https://api.kite.trade")
    KITE_MASTER_DATA_FILE_PATH = os.getenv("KITE_MASTER_DATA_FILE_PATH", "kite_master_data.csv")
    DOWNLOAD_XTS_MASTER_DATA = os.getenv("DOWNLOAD_XTS_MASTER_DATA", "True").lower() == "true"
    XTS_BASE_URL = os.getenv("XTS_BASE_URL", "https://ttblaze.iifl.com")
    XTS_MASTER_DATA_FILE_PATH = os.getenv("XTS_MASTER_DATA_FILE_PATH", "xts_master_data.csv")
    UPSTOX_MASTER_DATA_FILE_PATH = os.getenv("UPSTOX_MASTER_DATA_FILE_PATH", "complete.json")
    INTERNAL_POSTBACK_TOKEN = os.getenv("INTERNAL_POSTBACK_TOKEN", "")
    REQUIRE_MASTER_DATA_ON_STARTUP = (
        os.getenv("REQUIRE_MASTER_DATA_ON_STARTUP", "False").lower() == "true"
    )
