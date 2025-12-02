import logging
from typing import Callable, Dict, Optional, List
from vk_api import VkApi
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
from src.database.crud import (
    get_bot_user_by_vk_id,
    save_user_from_vk,
    save_search_results,
    get_next_search_profile,
    add_to_favorites,
    add_to_viewed,
    get_profile_by_vk_id,
    create_or_update_search_preferences,
    get_search_preferences,
    get_profile_photos,
    add_photos_to_profile,
    get_favorites
)
from src.vk_bot.keyboards import VkBotKeyboards
from src.database.base import Session
from src.database.statemanager import StateManager
from src.vk_bot.vk_client import VKUser
from src.vk_bot.vk_searcher import VKSearcher

logger = logging.getLogger(__name__)

def state_handler(state_name):
    def decorator(func):
        func.state_name = state_name
        return func
    return decorator

class VkBot:

    FIELD_NAMES_RU = {
        "first_name": "имя",
        "last_name": "фамилию",
        "vk_link": "ссылку на профиль",
        "age": "возраст",
        "sex": "пол",
        "city": "город"
    }

    def __init__(self, token) -> None:
        self.__token = token
        self.vk_session = VkApi(token=self.__token)
        self.longpoll = VkLongPoll(self.vk_session)
        self.vk = self.vk_session.get_api()

        # Инициализируем VKSearcher
        self.vk_searcher = VKSearcher(token)

        # Инициализируем клавиатуры
        self.keyboard = VkBotKeyboards.create_main_keyboard()
        self.search_keyboard = VkBotKeyboards.create_search_keyboard()
        self.viewing_keyboard = VkBotKeyboards.create_viewing_keyboard()
        self.settings_keyboard = VkBotKeyboards.create_settings_keyboard()

        self.state_manager = StateManager()
        self.state_handlers: Dict[str, Callable] = self._collect_state_handlers()

    def _collect_state_handlers(self) -> dict:
        handlers = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, "state_name"):
                handlers[attr.state_name] = attr
        return handlers

    def send_msg(self, user_id: int, message: str, keyboard: Optional[VkKeyboard] = None):
        params = {
            "user_id": user_id,
            "message": message,
            "random_id": get_random_id()
        }
        if keyboard:
            params["keyboard"] = keyboard.get_keyboard()

        self.vk.messages.send(**params)
        logger.info(f"Отправлено сообщение пользователю {user_id}: {message}")

    def show_user_profile(self, user_id: int):
        with Session() as session:
            user_info = get_bot_user_by_vk_id(session, user_id)
            if user_info is not None:
                user_data = {
                    "first_name": user_info.first_name,
                    "last_name": user_info.last_name,
                    "age": user_info.age,
                    "sex": "Мужской" if user_info.sex == 2 else "Женский" if user_info.sex == 1 else "Не указан",
                    "city": user_info.city,
                    "vk_link": f"https://vk.com/id{user_info.vk_id}",
                    "vk_id": user_info.vk_id
                }
            else:
                # если пользователя нет в базе, берём данные из StateManager
                user_data = self.state_manager.get_data(user_id) or {}

            lines = []

            for key in ["first_name", "last_name", "age", "sex", "city", "vk_link"]:
                field_name = self.FIELD_NAMES_RU.get(key, key)
                value = user_data.get(key)
                if value is None or (isinstance(value, str) and not value.strip()):
                    value = "не указан"
                lines.append(f"{field_name.capitalize()}: {value}")

            message = "Ваша анкета:\n\n" + "\n".join(lines)
            self.send_msg(user_id, message)

    @state_handler("fill_missing_fields")
    def handle_fill_missing_fields(self, user_id: int, text: str):
        user_data = self.state_manager.get_data(user_id) or {}
        required_fields = ["first_name", "last_name", "vk_link", "age", "sex", "city"]

        # Заполняем первое пустое поле
        for field in required_fields:
            if not user_data.get(field):
                user_data[field] = text.strip()
                break

        data_to_save = user_data.copy()
        if 'vk_id' in data_to_save:
            del data_to_save['vk_id']

        self.state_manager.set_data(user_id, **data_to_save)

        # Проверка недостающих полей
        missing_fields = [rf for rf in required_fields if not user_data.get(rf)]
        if missing_fields:
            missing_fields_text = ", ".join(self.FIELD_NAMES_RU[f] for f in missing_fields)
            self.send_msg(user_id, f"Пожалуйста, укажите {missing_fields_text}:")
            return

        # Сохраняем пользователя в БД (с сессией)
        with Session() as session:
            save_user_from_vk(
                session,
                vk_id=int(user_data["vk_id"]),
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                vk_link=user_data["vk_link"],
                age=int(user_data["age"]),
                sex=user_data["sex"],
                city=user_data["city"]
            )
        self.show_user_profile(user_id)
        self.state_manager.clear_state(user_id)
        self.send_msg(user_id, "Данные профиля сохранены", keyboard=self.keyboard)
        logger.info(f"Пользователь {user_id} сохранён: {user_data}")

    def start_search(self, user_id: int):
        """Начало поиска"""
        with Session() as session:
            # Получаем пользователя
            user = get_bot_user_by_vk_id(session, user_id)
            if not user:
                self.send_msg(user_id, "Сначала заполните профиль!", keyboard=self.keyboard)
                return

            # Создаем дефолтные настройки поиска, если их нет
            preferences = get_search_preferences(session, user.id)
            if not preferences:
                # Используем данные пользователя для поиска противоположного пола
                search_sex = 1 if user.sex == 2 else 2 if user.sex == 1 else 0
                search_city = user.city

                preferences = create_or_update_search_preferences(
                    session,
                    bot_user_id=user.id,
                    search_sex=search_sex,
                    search_age_min=18,
                    search_age_max=35,
                    search_city=search_city
                )

            # Ищем пользователей
            found_users = self.vk_searcher.search_users(
                city=preferences.search_city or user.city,
                age_from=preferences.search_age_min,
                age_to=preferences.search_age_max,
                sex=preferences.search_sex or 0,
                count=20
            )

            if not found_users:
                self.send_msg(user_id, "По вашему запросу никого не найдено :(", keyboard=self.keyboard)
                return

            # Сохраняем результаты
            saved_profiles = save_search_results(session, user.id, found_users)

            if saved_profiles:
                self.send_msg(user_id, f"Найдено {len(saved_profiles)} анкет! Показываю первую...",
                              keyboard=self.viewing_keyboard)
                self.show_next_profile(user_id)
            else:
                self.send_msg(user_id, "Не удалось сохранить результаты поиска", keyboard=self.keyboard)

    def show_next_profile(self, user_id: int):
        """Показать следующий профиль"""
        with Session() as session:
            profile = get_next_search_profile(session, user_id)
            if not profile:
                self.send_msg(user_id, "Больше нет анкет для просмотра!", keyboard=self.keyboard)
                return

            # Получаем фото профиля
            photos = get_profile_photos(session, profile.id)

            # Формируем сообщение
            message = f"👤 {profile.first_name} {profile.last_name}\n"
            message += f"🔗 {profile.profile_url}\n"
            if profile.age:
                message += f"🎂 {profile.age} лет\n"
            if profile.city:
                message += f"📍 {profile.city}\n"

            if photos:
                message += "\n📸 Фотографии:\n"
                for i, photo in enumerate(photos[:3], 1):
                    message += f"{i}. {photo.photo_url}\n"
            else:
                message += "\n📸 Фотографии отсутствуют\n"

            self.send_msg(user_id, message, keyboard=self.viewing_keyboard)

            # Добавляем в просмотренные
            user = get_bot_user_by_vk_id(session, user_id)
            if user:
                add_to_viewed(session, user.id, profile.id)

    def show_favorites(self, user_id: int):
        """Показать избранное"""
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if not user:
                self.send_msg(user_id, "Сначала заполните профиль!", keyboard=self.keyboard)
                return

            favorites = get_favorites(session, user.id)
            if not favorites:
                self.send_msg(user_id, "У вас пока нет избранных анкет.", keyboard=self.keyboard)
                return

            message = "❤️ Ваши избранные:\n\n"
            for i, profile in enumerate(favorites, 1):
                message += f"{i}. {profile.first_name} {profile.last_name}\n"
                message += f"   {profile.profile_url}\n"
                if profile.age:
                    message += f"   Возраст: {profile.age} лет\n"
                if profile.city:
                    message += f"   Город: {profile.city}\n"
                message += "\n"

            self.send_msg(user_id, message, keyboard=self.keyboard)

    def add_to_favorites_handler(self, user_id: int):
        """Добавить текущий профиль в избранное"""
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if not user:
                self.send_msg(user_id, "Ошибка: пользователь не найден", keyboard=self.keyboard)
                return

            # Получаем последний просмотренный профиль
            # (в реальности нужно отслеживать текущий профиль в состоянии)
            # Временная реализация: находим первый непросмотренный профиль
            profile = get_next_search_profile(session, user_id)
            if not profile:
                self.send_msg(user_id, "Нет профиля для добавления в избранное", keyboard=self.keyboard)
                return

            # Проверяем, не добавлен ли уже
            from src.database.crud import is_in_favorites
            if is_in_favorites(session, user.id, profile.id):
                self.send_msg(user_id, "Этот профиль уже в избранном!", keyboard=self.viewing_keyboard)
                return

            # Добавляем в избранное
            add_to_favorites(session, user.id, profile.id)
            self.send_msg(user_id, f"✅ {profile.first_name} {profile.last_name} добавлен(а) в избранное!",
                          keyboard=self.viewing_keyboard)

    def handle_message(self, user_id: int, text: str):
        logger.info(f"Новое сообщение от {user_id}: {text}")

        text_lower = text.lower()

        if text_lower in ["/start", "старт", "начать"]:
            with Session() as session:
                # Если пользователь уже есть в базе
                user_in_db = get_bot_user_by_vk_id(session, user_id)
                if user_in_db:
                    self.send_msg(user_id, "Вы уже начали работу с ботом. Вот ваша анкета:", keyboard=self.keyboard)
                    self.show_user_profile(user_id)
                    return

            self.send_msg(user_id, "Привет! Я бот для знакомств 🔥", keyboard=self.keyboard)
            self.state_manager.set_state(user_id, "start")

            # Получаем данные пользователя из VK
            vk_user = VKUser(access_token=self.__token, user_id=user_id)
            vk_info = vk_user.user_info()

            if not vk_info or not vk_info.get("vk_id"):
                self.send_msg(user_id, "Не удалось получить ваши данные из VK. Попробуйте позже.")
                return

            # Удаляем vk_id из vk_info перед передачей в set_data
            vk_info_without_id = vk_info.copy()
            if 'vk_id' in vk_info_without_id:
                del vk_info_without_id['vk_id']

            self.state_manager.set_data(user_id, **vk_info_without_id)
            self.show_user_profile(user_id)

            # Проверка недостающих полей
            user_data = {**vk_info, **(self.state_manager.get_data(user_id) or {})}
            required_fields = ["first_name", "last_name", "vk_link", "age", "sex", "city"]
            missing_fields = [f for f in required_fields if not user_data.get(f)]
            if missing_fields:
                # Удаляем vk_id из user_data перед передачей в set_data
                user_data_without_id = user_data.copy()
                if 'vk_id' in user_data_without_id:
                    del user_data_without_id['vk_id']

                self.state_manager.set_data(user_id, **user_data_without_id)
                self.state_manager.set_state(user_id, "fill_missing_fields")
                missing_fields_text = ", ".join(self.FIELD_NAMES_RU[f] for f in missing_fields)
                self.send_msg(user_id, f"Пожалуйста, укажите {missing_fields_text}:")
            else:
                with Session() as session:
                    save_user_from_vk(
                        session,
                        vk_id=int(user_data["vk_id"]),
                        first_name=user_data["first_name"],
                        last_name=user_data["last_name"],
                        vk_link=user_data["vk_link"],
                        age=int(user_data["age"]),
                        sex=user_data["sex"],
                        city=user_data["city"]
                    )
                self.send_msg(user_id, "Данные профиля сохранены ✅", keyboard=self.keyboard)
                logger.info(f"Пользователь {user_id} сохранён: {user_data}")

            return

        current_state = self.state_manager.get_state(user_id)
        if current_state and current_state in self.state_handlers:
            handler = self.state_handlers[current_state]
            handler(user_id, text)
            return

        # Обработка команд главного меню
        if text_lower == "поиск":
            self.start_search(user_id)
            return

        if text_lower == "избранное":
            self.show_favorites(user_id)
            return

        # Обработка команд во время просмотра анкет
        if text_lower in ["➡️ далее", "далее", "next"]:
            self.show_next_profile(user_id)
            return

        if text_lower in ["❤️ в избранное", "в избранное", "избранное", "лайк"]:
            self.add_to_favorites_handler(user_id)
            return

        if text_lower == "помощь":
            help_text = (
                "🤖 Помощь по командам:\n\n"
                "🔥 Основные команды:\n"
                "• Поиск - Начать поиск анкет\n"
                "• Избранное - Показать избранные анкеты\n"
                "• Настройки - Настройки поиска\n"
                "• Помощь - Эта справка\n\n"
                "👁️ Во время просмотра:\n"
                "• Далее - Следующая анкета\n"
                "• В избранное - Добавить в избранное\n"
                "• Не нравится - Пропустить анкету\n"
                "• В меню - Вернуться в главное меню"
            )
            self.send_msg(user_id, help_text, keyboard=self.keyboard)
            return

        if text_lower == "настройки":
            self.send_msg(user_id, "Настройки поиска скоро будут доступны!", keyboard=self.settings_keyboard)
            return

        if text_lower == "назад":
            self.send_msg(user_id, "Возвращаемся в главное меню", keyboard=self.keyboard)
            return

        # Если команда не распознана
        self.send_msg(user_id, "Не понял команду. Напишите 'Помощь' для списка команд.", keyboard=self.keyboard)

    def run(self) -> None:
        logger.info("Бот запущен")
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                request = event.text
                user_id = event.user_id
                if user_id and request:
                    self.handle_message(user_id, request)