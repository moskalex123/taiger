from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
import os
from .i18n import I18n

class BotKeyboards:
    @staticmethod
    def main_menu(user_id: int, has_phone_number: bool = True) -> None:
        """Main menu - no inline keyboard buttons, all functionality in reply keyboard"""
        return None

    @staticmethod
    def profile_menu(lang: str = 'en') -> InlineKeyboardMarkup:
        """Profile menu keyboard"""
        toggle_to = "ru" if lang == "en" else "en"
        keyboard = [
            [InlineKeyboardButton(I18n.get(lang, "buttons.balance"), callback_data="balance")],
            [InlineKeyboardButton(I18n.get(lang, "buttons.lang_toggle"), callback_data=f"set_lang_{toggle_to}")],
            [InlineKeyboardButton(I18n.get(lang, "buttons.back"), callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def worker_controls(lang: str = 'en') -> InlineKeyboardMarkup:
        """Worker control keyboard with Start, Stop, and Status buttons"""
        keyboard = [
            [
                InlineKeyboardButton(I18n.get(lang, "buttons.start"), callback_data="worker_start"),
                InlineKeyboardButton(I18n.get(lang, "buttons.stop"), callback_data="worker_stop"),
                InlineKeyboardButton(I18n.get(lang, "buttons.status"), callback_data="worker_status")
            ],
            [InlineKeyboardButton(I18n.get(lang, "buttons.back"), callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def balance_menu(lang: str = 'en') -> InlineKeyboardMarkup:
        """Balance and account menu"""
        keyboard = [
            [
                InlineKeyboardButton(I18n.get(lang, "buttons.earn_battery"), callback_data="earn_battery"),
                InlineKeyboardButton(I18n.get(lang, "buttons.buy_battery"), callback_data="buy_battery")
            ],
            [InlineKeyboardButton(I18n.get(lang, "buttons.back"), callback_data="profile")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def buy_batteries_menu(lang: str = 'en') -> InlineKeyboardMarkup:
        """Buy batteries menu with different package options"""
        keyboard = [
            [
                InlineKeyboardButton(I18n.get(lang, "buttons.buy_1_battery"), callback_data="buy_battery:1"),
                InlineKeyboardButton(I18n.get(lang, "buttons.buy_5_batteries"), callback_data="buy_battery:5")
            ],
            [
                InlineKeyboardButton(I18n.get(lang, "buttons.buy_10_batteries"), callback_data="buy_battery:10"),
                InlineKeyboardButton(I18n.get(lang, "buttons.buy_25_batteries"), callback_data="buy_battery:25")
            ],
            [
                InlineKeyboardButton(I18n.get(lang, "buttons.buy_50_batteries"), callback_data="buy_battery:50"),
                InlineKeyboardButton(I18n.get(lang, "buttons.buy_100_batteries"), callback_data="buy_battery:100")
            ],
            [InlineKeyboardButton(I18n.get(lang, "buttons.back"), callback_data="balance")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def earn_battery_menu(lang: str = 'en') -> InlineKeyboardMarkup:
        """Earn battery menu with claim button"""
        keyboard = [
            [InlineKeyboardButton(I18n.get(lang, "buttons.claim_battery"), callback_data="claim_battery")],
            [InlineKeyboardButton(I18n.get(lang, "buttons.back"), callback_data="balance")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirm_worker_stop(lang: str = 'en') -> InlineKeyboardMarkup:
        """Confirmation keyboard for stopping worker"""
        keyboard = [
            [
                InlineKeyboardButton(I18n.get(lang, "buttons.yes_stop"), callback_data="worker_stop_confirm"),
                InlineKeyboardButton(I18n.get(lang, "buttons.cancel"), callback_data="worker")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_to_main(lang: str = 'en') -> InlineKeyboardMarkup:
        """Simple back to main menu keyboard"""
        keyboard = [[InlineKeyboardButton(I18n.get(lang, "buttons.back"), callback_data="main_menu")]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def logs_menu(lang: str = 'en') -> InlineKeyboardMarkup:
        """Logs viewing menu"""
        webapp_url = os.getenv("TELEGRAM_WEBAPP_URL", "https://yourdomain.com/tma")
        app_version = os.getenv("APP_VERSION", "5")
        if "?" in webapp_url:
            webapp_url_with_version = f"{webapp_url}&v={app_version}"
        else:
            webapp_url_with_version = f"{webapp_url}?v={app_version}"

        keyboard = [
            [InlineKeyboardButton(I18n.get(lang, "buttons.view_in_app"), web_app={"url": f"{webapp_url_with_version}#/logs"})],
            [
                InlineKeyboardButton(I18n.get(lang, "buttons.refresh"), callback_data="logs"),
                InlineKeyboardButton(I18n.get(lang, "buttons.back"), callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def tma_menu(lang: str = 'en') -> InlineKeyboardMarkup:
        """TMA launch menu with Mini App and Worker buttons"""
        webapp_url = os.getenv("TELEGRAM_WEBAPP_URL", "https://yourdomain.com/tma")
        app_version = os.getenv("APP_VERSION", "5")
        if "?" in webapp_url:
            webapp_url_with_version = f"{webapp_url}&v={app_version}"
        else:
            webapp_url_with_version = f"{webapp_url}?v={app_version}"

        keyboard = [
            [InlineKeyboardButton(I18n.get(lang, "buttons.open_mini_app"), web_app={"url": webapp_url_with_version})],
            [InlineKeyboardButton(I18n.get(lang, "buttons.worker"), callback_data="worker")],
            [InlineKeyboardButton(I18n.get(lang, "buttons.back"), callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def reply_keyboard(lang: str = 'en') -> ReplyKeyboardMarkup:
        """Reply keyboard with three buttons: Settings, Launch TMA, and Profile"""
        from telegram import ReplyKeyboardMarkup

        keyboard = [
            [I18n.get(lang, "buttons.settings")],
            [I18n.get(lang, "buttons.tma")],
            [I18n.get(lang, "buttons.profile")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    @staticmethod
    def settings_menu(lang: str = 'en') -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton(I18n.get(lang, "buttons.change_model_1"), callback_data="change_model_1")],
            [InlineKeyboardButton(I18n.get(lang, "buttons.change_model_2"), callback_data="change_model_2")],
            [InlineKeyboardButton(I18n.get(lang, "buttons.change_instruction"), callback_data="bot_settings_prompt")],
            [InlineKeyboardButton(I18n.get(lang, "buttons.back"), callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def ai_slots_menu(slot1_label: str, slot2_label: str, lang: str = 'en') -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton(f"{I18n.get(lang, 'buttons.slot_1')} {slot1_label}", callback_data="choose_slot_1")],
            [InlineKeyboardButton(f"{I18n.get(lang, 'buttons.slot_2')} {slot2_label}", callback_data="choose_slot_2")],
            [InlineKeyboardButton(I18n.get(lang, "buttons.back"), callback_data="bot_settings")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def models_for_slot_menu(options: list, slot_index: int, lang: str = 'en') -> InlineKeyboardMarkup:
        rows = []
        # Кнопка отключения слота отдельной строкой
        rows.append([InlineKeyboardButton(I18n.get(lang, "buttons.none"), callback_data=f"set_none:{slot_index}")])
        # Каждую модель показываем отдельной строкой
        for label, value in options:
            if value != "none":
                rows.append([InlineKeyboardButton(label, callback_data=f"set_model:{slot_index}:{value}")])
        rows.append([InlineKeyboardButton(I18n.get(lang, "buttons.back"), callback_data="bot_settings")])
        return InlineKeyboardMarkup(rows)

    @staticmethod
    def prompt_menu(lang: str = 'en') -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton(I18n.get(lang, "buttons.back") + " to Settings", callback_data="bot_settings")]
        ]
        return InlineKeyboardMarkup(keyboard)
