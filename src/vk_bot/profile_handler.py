from telegram import Update
from telegram.ext import ContextTypes
from src.vk_bot.keyboards import KeyboardManager


class ProfileHandler:
    """Обработчик заполнения профиля пользователя"""

    def __init__(self):
        self.profile_data = {}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user

        # Проверяем, есть ли пользователь в базе
        db = context.bot_data.get('db')
        if db:
            from src.database.crud import User
            existing_user = db.query(User).filter(User.telegram_id == user.id).first()
            if existing_user:
                await update.message.reply_text(
                    f"С возвращением, {user.first_name}! 👋\n"
                    "Я помогу вам найти интересных людей для общения.\n\n"
                    "Выберите действие:",
                    reply_markup=KeyboardManager.get_main_menu()
                )
                return "START"

        # Если пользователя ещё нет в БД
        await update.message.reply_text(
            f"Привет, {user.first_name}! 👋\n"
            "Добро пожаловать в бот для знакомств!\n\n"
            "Для начала использования нужно заполнить ваш профиль.\n"
            "Как вас зовут? (Имя и Фамилия)",
            reply_markup=KeyboardManager.get_cancel_keyboard()
        )
        return "FILLING_PROFILE"

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена текущего действия"""
        await update.message.reply_text(
            "Действие отменено.",
            reply_markup=KeyboardManager.get_main_menu()
        )
        return "START"

    async def get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение имени пользователя"""
        name_parts = update.message.text.split()
        if len(name_parts) < 2:
            await update.message.reply_text(
                "Пожалуйста, введите имя и фамилию через пробел:\n"
            )
            return "FILLING_PROFILE"

        self.profile_data['firstname'] = name_parts[0]
        self.profile_data['lastname'] = name_parts[1]

        await update.message.reply_text(
            "Отлично! Теперь введите ваш возраст:",
            reply_markup=KeyboardManager.get_cancel_keyboard()
        )
        return "FILLING_PROFILE"

    async def get_age(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение возраста"""
        try:
            age = int(update.message.text)
            if age < 18 or age > 100:
                await update.message.reply_text(
                    "Пожалуйста, введите реальный возраст (18-100):"
                )
                return "FILLING_PROFILE"

            self.profile_data['age'] = age

            await update.message.reply_text(
                "Теперь выберите ваш пол:",
                reply_markup=KeyboardManager.get_gender_keyboard()
            )
            return "FILLING_PROFILE"
        except ValueError:
            await update.message.reply_text(
                "Пожалуйста, введите число (ваш возраст):"
            )
            return "FILLING_PROFILE"

    async def get_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение пола"""
        gender_text = update.message.text.lower()
        from src.database.crud import User  # Импорт здесь чтобы избежать циклических зависимостей

        if gender_text == "мужской":
            self.profile_data['gender'] = User.male
        elif gender_text == "женский":
            self.profile_data['gender'] = User.female
        else:
            await update.message.reply_text(
                "Пожалуйста, выберите пол из предложенных вариантов:",
                reply_markup=KeyboardManager.get_gender_keyboard()
            )
            return "FILLING_PROFILE"

        await update.message.reply_text(
            "В каком городе вы находитесь?",
            reply_markup=KeyboardManager.get_cancel_keyboard()
        )
        return "FILLING_PROFILE"

    async def get_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение города"""
        self.profile_data['city'] = update.message.text

        # Запрашиваем ссылку VK
        await update.message.reply_text(
            "Введите ссылку на ваш профиль VK:",
            reply_markup=KeyboardManager.get_skip_cancel_keyboard()
        )
        return "FILLING_PROFILE"

    async def get_vk_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение ссылки VK"""
        if update.message.text != "Пропустить":
            self.profile_data['user_vk_link'] = update.message.text
        else:
            self.profile_data['user_vk_link'] = None

        # Показываем сводку и запрашиваем подтверждение
        from src.database.crud import Gender

        profile_summary = (
            "Проверьте ваши данные:\n\n"
            f"👤 Имя: {self.profile_data['firstname']} {self.profile_data['lastname']}\n"
            f"🎂 Возраст: {self.profile_data['age']}\n"
            f"🚻 Пол: {'Мужской' if self.profile_data['gender'] == Gender.male else 'Женский'}\n"
            f"🏙️ Город: {self.profile_data['city']}\n"
            f"🔗 VK: {self.profile_data.get('user_vk_link', 'не указан')}"
        )

        await update.message.reply_text(
            profile_summary,
            reply_markup=KeyboardManager.get_confirmation_keyboard()
        )
        return "FILLING_PROFILE"

    async def save_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сохранение профиля в базу данных"""
        db = context.bot_data.get('db')
        user = update.effective_user

        if db:
            try:
                from src.database.crud import User
                # Создаем пользователя в базе
                new_user = User(
                    telegram_id=user.id,
                    firstname=self.profile_data['firstname'],
                    lastname=self.profile_data['lastname'],
                    age=self.profile_data['age'],
                    gender=self.profile_data['gender'],
                    city=self.profile_data['city'],
                    user_vk_link=self.profile_data.get('user_vk_link')
                )

                db.add(new_user)
                db.commit()

                await update.message.reply_text(
                    "✅ Ваш профиль успешно создан!\n\n"
                    "Теперь вы можете начать поиск интересных людей.",
                    reply_markup=KeyboardManager.get_main_menu()
                )

                # Очищаем временные данные
                self.profile_data.clear()

                return "START"

            except Exception as e:
                await update.message.reply_text(
                    "❌ Произошла ошибка при сохранении профиля. "
                    "Попробуйте позже или обратитесь в поддержку."
                )
                return "START"

        await update.message.reply_text(
            "❌ Ошибка подключения к базе данных.",
            reply_markup=KeyboardManager.get_main_menu()
        )
        return "START"