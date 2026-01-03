"""
Database utilities for Universal AI Text Processor
"""
import os
import asyncio
import asyncpg
from typing import List, Dict, Any, Optional


class DatabaseUtils:
    """Utility class for database operations"""
    
    def __init__(self, logger=None):
        self.logger = logger
        self.db_config = {
            'host': os.getenv('DB_HOST', '94.141.161.21'),
            'port': int(os.getenv('DB_PORT', '5433')),
            'database': os.getenv('DB_NAME', 'taigerdb'),
            'user': os.getenv('DB_USER', 'taiger'),
            'password': os.getenv('DB_PASSWORD', 'Pp969291')
        }
    
    async def get_all_models(self) -> List[Dict[str, Any]]:
        """
        Fetch all models from the database.
        
        Returns:
            List of model dictionaries
        """
        try:
            conn = await asyncpg.connect(**self.db_config)
            try:
                rows = await conn.fetch('''
                    SELECT id, model, system_content, user_content,
                           max_tokens, temperature, top_p,
                           price_per_post, provider,
                           model_visible_name, api_price, visible
                    FROM models
                    ORDER BY id
                ''')
                
                models = []
                for row in rows:
                    visible_name = row['model_visible_name']
                    if self.logger and not visible_name:
                        self.logger.debug(
                            "Model %s (%s) missing model_visible_name, falling back to technical name",
                            row['id'],
                            row['model']
                        )
                    models.append({
                        'id': row['id'],
                        'model': row['model'],
                        'system_content': row['system_content'] or '',
                        'user_content': row['user_content'] or '',
                        'max_tokens': row['max_tokens'] or 500,
                        'temperature': row['temperature'] or 0.7,
                        'top_p': row['top_p'] or 0.9,
                        'price_per_post': row['price_per_post'] or 0.0,
                        'provider': row['provider'] or 0,  # Default to Hyperbolic
                        'model_visible_name': visible_name,
                        'api_price': row['api_price'],
                        'visible': row['visible']
                    })
                
                return models
            finally:
                await conn.close()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Database error fetching models: {e}")
            return []
    
    async def get_model_by_id(self, model_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific model by ID from the database.
        
        Args:
            model_id: ID of the model to fetch
            
        Returns:
            Model dictionary or None if not found
        """
        try:
            conn = await asyncpg.connect(**self.db_config)
            try:
                row = await conn.fetchrow('''
                    SELECT id, model, system_content, user_content,
                           max_tokens, temperature, top_p,
                           price_per_post, provider,
                           model_visible_name, api_price, visible
                    FROM models
                    WHERE id = $1
                ''', model_id)
                
                if row:
                    visible_name = row['model_visible_name']
                    if self.logger and not visible_name:
                        self.logger.debug(
                            "Model %s (%s) missing model_visible_name, falling back to technical name",
                            row['id'],
                            row['model']
                        )
                    return {
                        'id': row['id'],
                        'model': row['model'],
                        'system_content': row['system_content'] or '',
                        'user_content': row['user_content'] or '',
                        'max_tokens': row['max_tokens'] or 500,
                        'temperature': row['temperature'] or 0.7,
                        'top_p': row['top_p'] or 0.9,
                        'price_per_post': row['price_per_post'] or 0.0,
                        'provider': row['provider'] or 0,  # Default to Hyperbolic
                        'model_visible_name': visible_name,
                        'api_price': row['api_price'],
                        'visible': row['visible']
                    }
                return None
            finally:
                await conn.close()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Database error fetching model {model_id}: {e}")
            return None