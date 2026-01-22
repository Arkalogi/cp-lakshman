from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from api.config import Config

engine = create_async_engine(Config.DATABASE_URL, echo=False, future=True)

DbAsyncSession = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)

