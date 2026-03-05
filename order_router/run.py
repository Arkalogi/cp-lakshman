import os
import uvicorn


if __name__ == "__main__":
    port = int(os.getenv("ORDER_ROUTER_PORT", "8001"))
    uvicorn.run("order_router.main:app", host="0.0.0.0", port=port, reload=True)
