from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


class KeyboardManager:
    """Менеджер клавиатур бота"""

    @staticmethod
    def get_main_menu():
        """Главное меню бота"""
        return ReplyKeyboardMarkup([
            ["Начать поиск", "Мой профиль"],
            ["Избранное", "Помощь"]
        ], resize_keyboard=True)

    @staticmethod
    def get_profile_actions():
        """Кнопки действий с анкетами"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❤️ Нравится", callback_data="like"),
                InlineKeyboardButton("👎 Не нравится", callback_data="dislike")
            ],
            [InlineKeyboardButton("🚫 Заблокировать", callback_data="block")],
            [InlineKeyboardButton("📌 В избранное", callback_data="favorite")]
        ])

    @staticmethod
    def get_gender_keyboard():
        """Клавиатура для выбора пола"""
        return ReplyKeyboardMarkup([
            ["Мужской", "Женский"],
            ["Отмена"]
        ], resize_keyboard=True)

    @staticmethod
    def get_confirmation_keyboard():
        """Клавиатура для подтверждения данных"""
        return ReplyKeyboardMarkup([
            ["✅ Всё верно", "🔄 Заполнить заново"],
            ["Отмена"]
        ], resize_keyboard=True)

    @staticmethod
    def get_cancel_keyboard():
        """Клавиатура с кнопкой отмены"""
        return ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True)

    @staticmethod
    def get_skip_cancel_keyboard():
        """Клавиатура с пропуском и отменой"""
        return ReplyKeyboardMarkup([["Пропустить", "Отмена"]], resize_keyboard=True)