import asyncio
from api.core.database import get_session_factory
from sqlalchemy import select
from api.models.db.workshop import Workshop
from api.models.db.workshop_instance import WorkshopInstance

async def main():
    async with get_session_factory()() as db:
        print("--- Templates ---")
        res = await db.execute(select(Workshop))
        for r in res.scalars().all():
            print(f"{r.name} ({r.id}) - Active: {r.is_active}")
        
        print("\n--- Instances ---")
        res = await db.execute(select(WorkshopInstance))
        for r in res.scalars().all():
            print(f"{r.k8s_name} ({r.id}) - Phase: {r.phase} - Terminated: {r.terminated_at}")

if __name__ == "__main__":
    asyncio.run(main())
