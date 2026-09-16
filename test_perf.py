import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.users.models import User
from sqlalchemy import select
from time import perf_counter

async def test_session_get_vs_select():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        from app.db.session import Base
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        for i in range(100):
            session.add(User(email=f"test{i}@test.com", first_name="test", last_name="test", password_hash="test"))
        await session.commit()

    async with async_session() as session:
        # Get one element so it's cached in the identity map
        user = await session.get(User, "test0@test.com")

        # Benchmark get
        start = perf_counter()
        for i in range(100):
            user = await session.get(User, "test0@test.com")
        get_time = perf_counter() - start

        # Benchmark select
        start = perf_counter()
        for i in range(100):
            result = await session.execute(select(User).where(User.email == "test0@test.com"))
            user = result.scalar_one_or_none()
        select_time = perf_counter() - start

        print(f"select time (cached): {select_time}")
        print(f"get time (cached): {get_time}")

if __name__ == "__main__":
    asyncio.run(test_session_get_vs_select())
