from telegram import Update
from telegram.ext import ContextTypes
from src.vk_bot.keyboards import KeyboardManager


class SearchHandler:
    """Обработчик поиска и просмотра анкет"""

    async def start_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало поиска анкет"""
        user = update.effective_user
        db = context.bot_data.get('db')

        if db:
            from src.database.crud import User
            # Проверяем, заполнен ли профиль
            existing_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not existing_user:
                await update.message.reply_text(
                    "❌ Сначала заполните ваш профиль!",
                    reply_markup=KeyboardManager.get_main_menu()
                )
                return "START"

        # Здесь должна быть логика получения следующей анкеты
        # Пока используем заглушку
        profile_text = (
            "Анна, 25 лет\n"
            "🏙️ Москва\n"
            "💼 Дизайнер\n"
            "❤️ Путешествия, искусство, музыка\n"
            "🔗 vk.com/anna_example"
        )

        await update.message.reply_text(
            "Начинаем поиск...\n\n" + profile_text,
            reply_markup=KeyboardManager.get_profile_actions()
        )

        return "VIEWING_PROFILES"

    async def handle_reaction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка реакций на анкеты"""
        query = update.callback_query
        await query.answer()

        action = query.data

        # Обработка разных действий
        if action == "like":
            response_text = "❤️ Вы поставили лайк! Если будет взаимность - сообщим!"
        elif action == "dislike":
            response_text = "👎 Анкета пропущена"
        elif action == "block":
            response_text = "🚫 Пользователь заблокирован"
        elif action == "favorite":
            response_text = "📌 Добавлено в избранное"

        await query.edit_message_text(
            f"{response_text}\n\nИщем следующую анкету..."
        )

        # Здесь должна быть логика получения следующей анкеты
        # Пока используем заглушку
        next_profile_text = (
            "Максим, 30 лет\n"
            "🏙️ Санкт-Петербург\n"
            "💼 Разработчик\n"
            "❤️ Спорт, программирование, книги\n"
            "🔗 vk.com/max_example"
        )

        await query.message.reply_text(
            next_profile_text,
            reply_markup=KeyboardManager.get_profile_actions()
        )

        return "VIEWING_PROFILES"