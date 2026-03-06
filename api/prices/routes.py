import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.prices.ws_hub import hub

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/prices")
async def prices_socket(websocket: WebSocket):
    await hub.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "message": "invalid JSON payload"}
                )
                continue
            if not isinstance(message, dict):
                await websocket.send_json(
                    {"type": "error", "message": "payload must be an object"}
                )
                continue
            await hub.handle(websocket, message)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Price websocket unexpected error.")
    finally:
        await hub.disconnect(websocket)
