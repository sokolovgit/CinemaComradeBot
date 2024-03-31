from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from app.database.models import Base
from config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=True)

async_session = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)