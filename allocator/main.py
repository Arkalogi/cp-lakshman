import asyncio
import logging

from fastapi import FastAPI

from api.data.local import MASTER_DATA, TOKEN_MAP
from api.data.utils import load_master_data
from api.workers import allocator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="CopyTrade Allocator")


@app.on_event("startup")
async def start_workers():
    logger.info("Loading master data")
    await load_master_data()
    app.state.master_data = MASTER_DATA
    app.state.token_map = TOKEN_MAP
    logger.info("Starting allocator worker")
    app.state.allocator_task = asyncio.create_task(allocator.thread_spawn_loop())


@app.on_event("shutdown")
async def stop_workers():
    task = getattr(app.state, "allocator_task", None)
    if task:
        logger.info("Stopping allocator worker")
        task.cancel()


@app.get("/health")
async def health_check():
    return {"status": "ok"}
