import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.demat_apis.routes import router as demat_apis_router
from api.demat_api_subscriptions.routes import router as demat_api_subscriptions_router
from api.strategies.routes import router as strategies_router
from api.strategy_subscriptions.routes import router as strategy_subscriptions_router
from api.users.routes import router as users_router
from api.orders.routes import router as orders_router
from api.workers import order_generator, allocator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="CopyTrade API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(strategies_router)
app.include_router(demat_apis_router)
app.include_router(demat_api_subscriptions_router)
app.include_router(strategy_subscriptions_router)
app.include_router(orders_router)


@app.on_event("startup")
async def start_workers():
    logger.info("Starting worker tasks")
    app.state.order_generator_task = asyncio.create_task(
        order_generator.thread_spawn_loop()
    )
    app.state.allocator_task = asyncio.create_task(allocator.thread_spawn_loop())


@app.on_event("shutdown")
async def stop_workers():
    tasks = [
        getattr(app.state, "order_generator_task", None),
        getattr(app.state, "allocator_task", None),
    ]
    tasks = [task for task in tasks if task]
    if tasks:
        logger.info("Stopping worker tasks")
        for task in tasks:
            task.cancel()


@app.get("/health")
async def health_check():
    return {"status": "ok"}
