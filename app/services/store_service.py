from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.store import Store, StoreSupervisorAssignment
from app.models.user import User


class StoreService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_assigned_store_ids(self, supervisor_id: str) -> List[str]:
        result = await self.db.execute(
            select(StoreSupervisorAssignment.store_id).where(
                StoreSupervisorAssignment.supervisor_id == supervisor_id
            )
        )
        return [row[0] for row in result.fetchall()]

    async def get_stores_for_user(self, user: User) -> List[Store]:
        if user.role == "hq_admin" or user.role == "marketer":
            result = await self.db.execute(select(Store).where(Store.is_active == True))
            return list(result.scalars().all())
        elif user.role == "supervisor":
            store_ids = await self.get_assigned_store_ids(user.id)
            if not store_ids:
                return []
            result = await self.db.execute(
                select(Store).where(Store.id.in_(store_ids), Store.is_active == True)
            )
            return list(result.scalars().all())
        elif user.role == "store_owner":
            if not user.store_id:
                return []
            result = await self.db.execute(
                select(Store).where(Store.id == user.store_id)
            )
            store = result.scalar_one_or_none()
            return [store] if store else []
        return []
