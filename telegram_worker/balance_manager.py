"""
Менеджер баланса пользователей
"""
from typing import Optional
from models import User, Model, ChannelPair


class BalanceManager:
    """Управление балансом пользователей"""
    
    def __init__(self, logger):
        self.logger = logger
    
    async def deduct_balance(self, db_session, user_id: int, model_id: Optional[int] = None) -> bool:
        """Deduct balance from user account."""
        try:
            amount = 0.001  # Default amount
            if model_id:
                model = await db_session.get(Model, model_id)
                if model and model.api_price is not None:
                    amount = model.api_price
                    self.logger.info(f"Using price {amount:.3f}🔋 from model '{model.model}'")
            
            user = await db_session.get(User, user_id)
            if not user:
                self.logger.warning("User not found for balance deduction")
                return False
            
            # Always deduct balance, even if it goes negative
            old_balance = user.balance
            user.balance = old_balance - amount
            await db_session.commit()
            # Refresh to get updated balance
            await db_session.refresh(user)
            new_balance = user.balance  # Сохраняем значение для избежания синхронного доступа
            self.logger.info(f"Balance deducted: {amount:.3f}🔋, new balance: {new_balance:.3f}🔋")
            return True
        except Exception as e:
            self.logger.error(f"Balance deduction failed: {e}")
            await db_session.rollback()
            return False
    
    async def send_insufficient_balance_notification(self, client, rule: ChannelPair, 
                                                   target_channel_id: int, notification_message: str,
                                                   determine_schedule_time_callback):
        """Send insufficient balance notification after successful post that resulted in negative balance."""
        try:
            # Calculate schedule time with the same interval as the rule
            scheduled_time = await determine_schedule_time_callback(rule, target_channel_id)
            
            # Send scheduled notification
            scheduled_msg = await client.send_message(
                chat_id=target_channel_id,
                text=notification_message,
                schedule_date=scheduled_time
            )
            
            if scheduled_msg:
                self.logger.info(f"Sent insufficient balance notification to {target_channel_id}")
        except Exception as e:
            self.logger.error(f"Failed to send insufficient balance notification: {e}", exc_info=True)