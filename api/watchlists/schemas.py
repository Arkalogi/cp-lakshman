from typing import Optional

from pydantic import BaseModel, Field


class WatchlistCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None
    instruments: list[int] = Field(default_factory=list)


class WatchlistUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class WatchlistInstrumentAddSchema(BaseModel):
    instrument_id: str



