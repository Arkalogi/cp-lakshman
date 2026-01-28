import asyncio
from typing import Optional, Dict


class PaperAPI:
    def __init__(self, api_id: str, api_key: str, api_secret: str):
        self.api_id = api_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.logged_in = False
        self.open_orders: Dict[str, dict] = {}
        self.completed_orders: Dict[str, dict] = {}
        self.cancelled_orders: Dict[str, dict] = {}

    async def generate_order_id(self) -> str:
        await asyncio.sleep(0.1)
        return "PAPER_ORDER_" + str(int(asyncio.get_event_loop().time() * 1000))

    async def login(self):
        await asyncio.sleep(1)
        self.logged_in = True
        return True

    async def place_order(self, order_details: dict):
        await asyncio.sleep(1)
        order_id = await self.generate_order_id()
        self.open_orders[order_id] = order_details
        return {"status": "success", "order_id": order_id}

    async def modify_order(self, order_id: str, new_details: dict):
        await asyncio.sleep(1)
        if order_id in self.open_orders:
            self.open_orders[order_id].update(new_details)
            return {"status": "success", "order_id": order_id}
        else:
            return {"status": "error", "message": "Order not found"}

    async def cancel_order(self, order_id: str):
        await asyncio.sleep(1)
        if order_id in self.open_orders:
            order_details = self.open_orders.pop(order_id)
            self.cancelled_orders[order_id] = order_details
            return {"status": "success", "order_id": order_id}
        else:
            return {"status": "error", "message": "Order not found"}

    async def get_order_last_update(self, order_id: str):
        await asyncio.sleep(1)
        if order_id in self.open_orders:
            return {"status": "success", "details": self.open_orders[order_id]}
        elif order_id in self.completed_orders:
            return {"status": "success", "details": self.completed_orders[order_id]}
        elif order_id in self.cancelled_orders:
            return {"status": "success", "details": self.cancelled_orders[order_id]}
        else:
            return {"status": "error", "message": "Order not found"}

    async def get_order_book(self):
        await asyncio.sleep(1)
        return {
            "open_orders": self.open_orders,
            "completed_orders": self.completed_orders,
            "cancelled_orders": self.cancelled_orders,
        }

    