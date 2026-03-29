import logging
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.demat_apis.routes import router as demat_apis_router
from api.strategies.routes import router as strategies_router
from api.strategy_subscriptions.routes import router as strategy_subscriptions_router
from api.users.routes import router as users_router
from api.orders.routes import router as orders_router
from api.signals.routes import router as signals_router
from api.master_data.routes import router as master_data_router
from api.watchlists.routes import router as watchlists_router
from api.prices.routes import router as prices_router
from api.data.utils import load_master_data, get_master_data_count
from api.config import Config
from api.order_routing import order_router_worker
from api.rms import rms_worker


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
app.include_router(strategy_subscriptions_router)
app.include_router(orders_router)
app.include_router(signals_router)
app.include_router(master_data_router)
app.include_router(watchlists_router)
app.include_router(prices_router)


@app.on_event("startup")
async def load_master_data_at_startup():
    loaded = await load_master_data()
    count = get_master_data_count()
    logger.info("Master data ready: loaded=%s count=%s", loaded, count)
    if count == 0:
        msg = "Master data load failed; no instruments available"
        if Config.REQUIRE_MASTER_DATA_ON_STARTUP:
            raise RuntimeError(msg)
        logger.warning("%s; continuing startup because REQUIRE_MASTER_DATA_ON_STARTUP=false", msg)
    if Config.ENABLE_RMS_WORKER:
        app.state.rms_task = asyncio.create_task(rms_worker.run_forever())
    if Config.ENABLE_ORDER_ROUTER_WORKER:
        app.state.order_router_task = asyncio.create_task(order_router_worker.run_forever())


@app.on_event("shutdown")
async def shutdown_background_tasks():
    task = getattr(app.state, "rms_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    task = getattr(app.state, "order_router_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@app.get("/health")
async def health_check():
    return {"status": "ok"}
