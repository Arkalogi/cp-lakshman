import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.demat_apis.routes import router as demat_apis_router
from api.strategies.routes import router as strategies_router
from api.strategy_subscriptions.routes import router as strategy_subscriptions_router
from api.users.routes import router as users_router
from api.orders.routes import router as orders_router
from api.signals.routes import router as signals_router


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


@app.get("/health")
async def health_check():
    return {"status": "ok"}
