import logging
from config import Config
from providers.upstox import UpstoxProvider

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting price feed with config: %s", Config.__dict__)
    upstox_provider = UpstoxProvider(
        api_key=Config.UPSTOX_API_KEY,
        api_secret=Config.UPSTOX_API_SECRET,
        redirect_url=Config.UPSTOX_REDIRECT_URL,
        mobile_number=Config.UPSTOX_MOBILE_NUMBER,
        totp_secret=Config.UPSTOX_TOTP_SECRET,
        pin=Config.UPSTOX_PIN,
    )
    upstox_provider.login()
    upstox_provider.start()
