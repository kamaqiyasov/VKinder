from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from keyboards import KeyboardManager
from profile_handler import ProfileHandler
from search_handler import SearchHandler


class BotManager:
    """Главный менеджер бота"""

    def __init__(self, token, db_session):
        self.application = Application.builder().token(token).build()
        self.db_session = db_session
        self.profile_handler = ProfileHandler()
        self.search_handler = SearchHandler()

        # Сохраняем сессию базы данных в bot_data
        self.application.bot_data['db'] = db_session

    def setup_handlers(self):
        """Настройка обработчиков"""
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.profile_handler.start)],
            states={
                "START": [
                    MessageHandler(filters.Regex('^Начать поиск$'), self.search_handler.start_search),
                    MessageHandler(filters.Regex('^Мой профиль$'), self.show_my_profile),
                    MessageHandler(filters.Regex('^Избранное$'), self.show_favorites),
                    MessageHandler(filters.Regex('^Помощь$'), self.help_command),
                ],
                "FILLING_PROFILE": [
                    MessageHandler(filters.Regex('^Отмена$'), self.profile_handler.cancel),
                    MessageHandler(filters.Regex('^✅ Всё верно$'), self.profile_handler.save_profile),
                    MessageHandler(filters.Regex('^🔄 Заполнить заново$'), self.profile_handler.start),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._route_profile_filling),
                ],
                "VIEWING_PROFILES": [
                    CallbackQueryHandler(self.search_handler.handle_reaction,
                                         pattern='^(like|dislike|block|favorite)$'),
                    MessageHandler(filters.Regex('^Отмена$'), self.profile_handler.cancel),
                ],
            },
            fallbacks=[CommandHandler('cancel', self.profile_handler.cancel)],
        )

        self.application.add_handler(conv_handler)

    async def _route_profile_filling(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Маршрутизация шагов заполнения профиля"""
        current_state = context.user_data.get('current_profile_step', 'name')

        if current_state == 'name':
            return await self.profile_handler.get_name(update, context)
        elif current_state == 'age':
            return await self.profile_handler.get_age(update, context)
        elif current_state == 'gender':
            return await self.profile_handler.get_gender(update, context)
        elif current_state == 'city':
            return await self.profile_handler.get_city(update, context)
        elif current_state == 'vk_link':
            return await self.profile_handler.get_vk_link(update, context)

    async def show_my_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ профиля пользователя"""
        user = update.effective_user
        db = context.bot_data.get('db')

        if db:
            from src.database.crud import User
            existing_user = db.query(User).filter(User.telegram_id == user.id).first()
            if existing_user:
                profile_text = (
                    "📋 Ваш профиль:\n\n"
                    f"👤 Имя: {existing_user.firstname} {existing_user.lastname}\n"
                    f"🎂 Возраст: {existing_user.age}\n"
                    f"🚻 Пол: {'Мужской' if existing_user.gender == User.male else 'Женский'}\n"
                    f"🏙️ Город: {existing_user.city}\n"
                    f"🔗 VK: {existing_user.user_vk_link or 'не указан'}"
                )

                await update.message.reply_text(
                    profile_text,
                    reply_markup=ReplyKeyboardMarkup([
                        ["Редактировать профиль", "В главное меню"]
                    ], resize_keyboard=True)
                )
                return "START"

        await update.message.reply_text(
            "❌ Профиль не найден. Заполните профиль сначала.",
            reply_markup=KeyboardManager.get_main_menu()
        )
        return "START"

    async def show_favorites(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ избранных анкет"""
        await update.message.reply_text(
            "❤️ Избранные анкеты:\n\n"
            "Пока здесь пусто. Добавляйте понравившихся людей в избранное!",
            reply_markup=KeyboardManager.get_main_menu()
        )
        return "START"

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Помощь по боту"""
        help_text = (
            "🤖 Помощь по боту:\n\n"
            "• Начать поиск - поиск анкет для знакомств\n"
            "• Мой профиль - просмотр и редактирование вашего профиля\n"
            "• Избранное - список понравившихся анкет\n"
            "• Помощь - это сообщение\n\n"
            "При просмотре анкет:\n"
            "❤️ - нравится\n"
            "👎 - не нравится\n"
            "🚫 - заблокировать пользователя\n"
            "📌 - добавить в избранное"
        )

        await update.message.reply_text(help_text, reply_markup=KeyboardManager.get_main_menu())
        return "START"

    def run(self):
        """Запуск бота"""
        self.setup_handlers()
        self.application.run_polling()