import asyncio
from api.core.database import get_session_factory
from sqlalchemy import select
from api.models.db.workshop import Workshop

async def main():
    async with get_session_factory()() as db:
        res = await db.execute(select(Workshop).where(Workshop.slug == 'bioconductor'))
        r = res.scalar_one_or_none()
        if r:
            print(f"Name: {r.name}, Storage: {r.storage}, Type: {type(r.storage)}")
        else:
            print("Template not found")

if __name__ == "__main__":
    asyncio.run(main())
