import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

class Config:
    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = os.getenv("REDIS_PORT", "6379")

    UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY")
    UPSTOX_API_SECRET = os.getenv("UPSTOX_API_SECRET")
    UPSTOX_REDIRECT_URL = os.getenv("UPSTOX_REDIRECT_URL")
    UPSTOX_MOBILE_NUMBER = os.getenv("UPSTOX_MOBILE_NUMBER")
    UPSTOX_TOTP_SECRET = os.getenv("UPSTOX_TOTP_SECRET")
    UPSTOX_PIN = os.getenv("UPSTOX_PIN")

    
