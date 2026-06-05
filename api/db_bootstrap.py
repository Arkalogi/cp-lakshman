import asyncio
import logging

from sqlalchemy import inspect, text

from api.data.database import engine
from api.data.models import Base

logger = logging.getLogger(__name__)


def _apply_schema_upgrades(conn) -> None:
    inspector = inspect(conn)
    table_names = set(inspector.get_table_names())

    if "strategy_subscriptions" in table_names:
        columns = {
            column["name"] for column in inspector.get_columns("strategy_subscriptions")
        }
        if "fund_deployed" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE strategy_subscriptions "
                    "ADD COLUMN fund_deployed FLOAT NOT NULL DEFAULT 0"
                )
            )
            logger.info("Added strategy_subscriptions.fund_deployed column.")

    if "orders" in table_names:
        columns = {column["name"] for column in inspector.get_columns("orders")}
        if "parent_tag" not in columns:
            conn.execute(
                text("ALTER TABLE orders ADD COLUMN parent_tag VARCHAR(50) NULL")
            )
            logger.info("Added orders.parent_tag column.")


async def bootstrap() -> None:
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_apply_schema_upgrades)
        logger.info("Database bootstrap completed.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(bootstrap())
