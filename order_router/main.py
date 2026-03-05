import asyncio
import logging

from fastapi import FastAPI

from api.workers import order_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="CopyTrade Order Router")


@app.on_event("startup")
async def start_workers():
    logger.info("Starting order router worker")
    app.state.order_router_task = asyncio.create_task(order_router.thread_spawn_loop())


@app.on_event("shutdown")
async def stop_workers():
    task = getattr(app.state, "order_router_task", None)
    if task:
        logger.info("Stopping order router worker")
        task.cancel()


@app.get("/health")
async def health_check():
    return {"status": "ok"}
