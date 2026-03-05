import os

import uvicorn


if __name__ == "__main__":
    port = int(os.getenv("ALLOCATOR_PORT", "8002"))
    uvicorn.run("allocator.main:app", host="0.0.0.0", port=port, reload=True)
