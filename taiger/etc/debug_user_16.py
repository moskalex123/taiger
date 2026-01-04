import asyncio
import os
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import User
from db import async_session

async def check_user_16():
    print("Checking user with id=16...")
    async with async_session() as session:
        try:
            # Check by internal ID
            result = await session.execute(select(User).where(User.id == 16))
            user = result.scalar_one_or_none()
            
            if user:
                print(f"User found: id={user.id}")
                print(f"  telegram_id: {user.telegram_id} (type: {type(user.telegram_id)})")
                print(f"  username: {user.username}")
                print(f"  first_name: {user.first_name}")
                print(f"  is_active: {user.is_active}")
                print(f"  is_superuser: {user.is_superuser}")
                
                # Check if there are duplicates by telegram_id
                if user.telegram_id:
                    result2 = await session.execute(select(User).where(User.telegram_id == user.telegram_id))
                    users_with_same_tg = result2.scalars().all()
                    print(f"Users with same telegram_id ({user.telegram_id}): {[u.id for u in users_with_same_tg]}")
            else:
                print("User with id=16 not found.")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_user_16())
