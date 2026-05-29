import asyncio
import os
import sys

# Ensure the root folder is on the python search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from app_backend.db.database import AsyncSessionLocal, engine
from app_backend.models.user import User
from app_backend.models.room import Room
from app_backend.models.message import Message

async def seed_data():
    print("Seeding database...")
    async with AsyncSessionLocal() as session:
        # TODO: Implement database seeding logic
        # 1. Create default chat rooms (general, random, tech)
        # 2. Create mock administrative or bot user
        # 3. Create initial hello messages
        print("Database seed complete.")

if __name__ == "__main__":
    asyncio.run(seed_data())
