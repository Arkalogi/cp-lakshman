import asyncio
import logging
from fastapi import FastAPI

from api.demat_apis.routes import router as demat_apis_router
from api.demat_api_subscriptions.routes import router as demat_api_subscriptions_router
from api.strategies.routes import router as strategies_router
from api.strategy_subscriptions.routes import router as strategy_subscriptions_router
from api.users.routes import router as users_router
from api.workers import order_generator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="CopyTrade API")

app.include_router(users_router)
app.include_router(strategies_router)
app.include_router(demat_apis_router)
app.include_router(demat_api_subscriptions_router)
app.include_router(strategy_subscriptions_router)


@app.on_event("startup")
async def start_workers():
    logger.info("Starting worker tasks")
    app.state.order_generator_task = asyncio.create_task(
        order_generator.thread_spawn_loop()
    )


@app.on_event("shutdown")
async def stop_workers():
    task = getattr(app.state, "order_generator_task", None)
    if task:
        logger.info("Stopping worker tasks")
        task.cancel()


@app.get("/health")
async def health_check():
    return {"status": "ok"}
