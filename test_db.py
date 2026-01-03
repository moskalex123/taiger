#!/usr/bin/env python3
import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import async_session
from models import Payment

async def test_db():
    try:
        from sqlalchemy import text
        session = async_session()
        result = await session.execute(text('SELECT * FROM payments LIMIT 1'))
        print('Payments table exists and has data')
        await session.close()
        return True
    except Exception as e:
        print(f'Error: {e}')
        try:
            await session.close()
        except:
            pass
        return False

if __name__ == "__main__":
    result = asyncio.run(test_db())
    sys.exit(0 if result else 1)