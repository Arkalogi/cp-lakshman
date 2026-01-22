from fastapi import FastAPI

from api.demat_apis.routes import router as demat_apis_router
from api.demat_api_subscriptions.routes import router as demat_api_subscriptions_router
from api.strategies.routes import router as strategies_router
from api.strategy_subscriptions.routes import router as strategy_subscriptions_router
from api.users.routes import router as users_router

app = FastAPI(title="CopyTrade API")

app.include_router(users_router)
app.include_router(strategies_router)
app.include_router(demat_apis_router)
app.include_router(demat_api_subscriptions_router)
app.include_router(strategy_subscriptions_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
