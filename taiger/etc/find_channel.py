#!/usr/bin/env python3
"""
Поиск канала по ID
"""
import asyncio
from db import async_session
from models import ChannelPair
from sqlalchemy import select, or_

async def find_channel():
    target_id = "3097329151"
    
    async with async_session() as session:
        # Ищем по точному совпадению
        result = await session.execute(
            select(ChannelPair).where(
                or_(
                    ChannelPair.source_channel == target_id,
                    ChannelPair.target_channel == target_id,
                    ChannelPair.source_channel == f"-{target_id}",
                    ChannelPair.target_channel == f"-{target_id}",
                    ChannelPair.source_channel == f"-100{target_id}",
                    ChannelPair.target_channel == f"-100{target_id}"
                )
            )
        )
        pairs = result.scalars().all()
        
        if pairs:
            print(f"✅ Найдены правила с каналом {target_id}:")
            for pair in pairs:
                print(f"   Правило {pair.id}: {pair.source_channel} -> {pair.target_channel} (пользователь {pair.user_id})")
        else:
            print(f"❌ Канал {target_id} не найден")
            
            # Покажем все каналы для справки
            all_result = await session.execute(select(ChannelPair))
            all_pairs = all_result.scalars().all()
            
            print(f"\n📋 Все каналы в системе:")
            for pair in all_pairs:
                print(f"   {pair.source_channel} -> {pair.target_channel} (пользователь {pair.user_id})")

if __name__ == "__main__":
    asyncio.run(find_channel())