import asyncio
import logging

from api.data.database import engine
from api.data.models import Base

logger = logging.getLogger(__name__)


async def bootstrap() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database bootstrap completed.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(bootstrap())
