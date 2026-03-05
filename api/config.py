import os


class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "mysql+aiomysql://root:admin@localhost:3306/copy_db")
    EXTERNAL_REQUEST_TIMEOUT = 10
    DATA_DIR = "data"
    DOWNLOAD_KITE_MASTER_DATA = True
    KITE_BASE_URL = "https://api.kite.trade"
    KITE_MASTER_DATA_FILE_PATH = "kite_master_data.csv"
    DOWNLOAD_XTS_MASTER_DATA = True
    XTS_BASE_URL = "https://ttblaze.iifl.com"
    XTS_MASTER_DATA_FILE_PATH = "xts_master_data.csv"
    INTERNAL_POSTBACK_TOKEN = os.getenv("INTERNAL_POSTBACK_TOKEN", "")
