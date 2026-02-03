from typing import Optional

from pydantic import BaseModel


class WatchlistCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None
    instruments: list[str] = []


class WatchlistUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instruments: Optional[list[str]] = None



