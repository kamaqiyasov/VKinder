import logging
import sys
from typing import Dict, List, Optional, Callable
from vk_api import VkApi
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard
from vk_api.utils import get_random_id

from src.database.base import Session
from src.database.crud import (
    get_bot_user_by_vk_id, save_user_from_vk, save_search_results,
    get_next_search_profile, add_to_favorites, add_to_viewed_profiles,
    create_or_update_search_preferences, get_search_preferences,
    add_photos_to_profile, get_favorites, is_in_favorites,
    is_in_blacklist, add_to_blacklist, delete_user_state,
    get_profile_by_vk_id, create_or_update_user_state, get_user_state
)
from src.vk_bot.keyboards import VkBotKeyboards
from src.database.statemanager import StateManager
from src.vk_bot.vk_searcher import VKSearcher
from src.database.models import Blacklist, ViewedProfiles
from sqlalchemy import text

logger = logging.getLogger(__name__)


def state_handler(state_name: str):
    """Декоратор для регистрации обработчиков состояний"""
    def decorator(func: Callable):
        func.state_name = state_name
        return func
    return decorator


class VkBot:
    """Основной класс бота VKinder"""

    FIELD_NAMES_RU = {
        "first_name": "имя",
        "last_name": "фамилию",
        "age": "возраст",
        "sex": "пол",
        "city": "город"
    }

    # Команды бота
    COMMANDS = {
        "start": ["/start", "старт", "начать"],
        "search": ["поиск"],
        "favorites": ["избранное"],
        "settings": ["настройки"],
        "help": ["помощь"],
        "next": ["➡️ далее", "далее", "next"],
        "like": ["❤️ в избранное", "в избранное", "избранное", "лайк"],
        "dislike": ["👎 в черный список", "не нравится", "в черный список", "черный список"],
        "menu": ["🔙 в меню", "в меню", "меню", "🏠 в меню"],
        "back": ["назад"]
    }

    def __init__(self, group_token: str, user_token: str) -> None:
        """Инициализация бота"""
        self._validate_tokens(group_token, user_token)

        self.vk_session = VkApi(token=group_token)
        self.longpoll = VkLongPoll(self.vk_session)
        self.vk = self.vk_session.get_api()
        self.vk_searcher = VKSearcher(user_token)

        # Инициализация клавиатур
        self.keyboards = {
            'main': VkBotKeyboards.create_main_keyboard(),
            'welcome': VkBotKeyboards.create_welcome_keyboard(),
            'search': VkBotKeyboards.create_search_keyboard(),
            'viewing': VkBotKeyboards.create_viewing_keyboard(),
            'settings': VkBotKeyboards.create_settings_keyboard()
        }

        self.state_manager = StateManager()
        self.state_handlers = self._collect_state_handlers()

        # Тест соединения
        self._test_connection()

    def _validate_tokens(self, group_token: str, user_token: str) -> None:
        """Валидация токенов"""
        logger.info("Проверка токенов...")

        if not group_token or group_token == "your_group_token_here":
            raise ValueError("Групповой токен не установлен. Проверьте .env файл")

        if not user_token or user_token == "your_user_token_here":
            raise ValueError("Пользовательский токен не установлен. Проверьте .env файл")

        logger.info("Токены прошли базовую проверку")

    def _collect_state_handlers(self) -> Dict[str, Callable]:
        """Сбор всех обработчиков состояний"""
        handlers = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, 'state_name'):
                handlers[attr.state_name] = attr
        return handlers

    def _test_connection(self) -> None:
        """Тестирование подключения к VK API"""
        logger.info("=== ТЕСТ ПОДКЛЮЧЕНИЯ К VK API ===")

        try:
            # Тест группового токена
            logger.info("Тестируем групповой токен...")
            group_info = self.vk.groups.getById()
            logger.info(f"Групповой токен работает. Группа: {group_info[0]['name']}")

            # Тест пользовательского токена
            logger.info("Тестируем пользовательский токен...")
            test_response = self.vk_searcher._make_request('users.get', {'user_ids': 1})

            if test_response:
                logger.info("Пользовательский токен работает")
            else:
                logger.error("Пользовательский токен не возвращает данные")

        except Exception as e:
            logger.error(f"Ошибка подключения к VK API: {e}")

        logger.info("=== ТЕСТ ПОДКЛЮЧЕНИЯ ЗАВЕРШЕН ===")

    def send_message(self, user_id: int, message: str,
                     keyboard: Optional[VkKeyboard] = None,
                     attachment: Optional[str] = None) -> None:
        """Отправка сообщения пользователю"""
        params = {
            "user_id": user_id,
            "message": message,
            "random_id": get_random_id()
        }

        if keyboard:
            params["keyboard"] = keyboard.get_keyboard()
        if attachment:
            params["attachment"] = attachment

        try:
            self.vk.messages.send(**params)
            logger.info(f"Отправлено сообщение пользователю {user_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")

    def _format_sex(self, sex_value) -> str:
        """Форматирование значения пола"""
        if sex_value is None:
            return "Не указан"

        if isinstance(sex_value, str):
            sex_lower = sex_value.lower()
            if sex_lower in ["женский", "female", "f", "1", "ж"]:
                return "Женский"
            elif sex_lower in ["мужской", "male", "m", "2", "м"]:
                return "Мужской"
            elif sex_lower in ["любой", "any", "0"]:
                return "Любой"

        elif isinstance(sex_value, int):
            if sex_value == 1:
                return "Женский"
            elif sex_value == 2:
                return "Мужской"
            elif sex_value == 0:
                return "Любой"

        return "Не указан"

    def _split_long_message(self, message: str, max_length: int = 4096) -> List[str]:
        """Разделение длинного сообщения на части"""
        if len(message) <= max_length:
            return [message]

        parts = []
        while len(message) > max_length:
            # Пытаемся разбить по переносу строки
            split_index = message.rfind('\n', 0, max_length)
            if split_index == -1:
                split_index = max_length
            parts.append(message[:split_index])
            message = message[split_index:].lstrip()

        if message:
            parts.append(message)

        return parts

    def handle_start_command(self, user_id: int, from_button: bool = False) -> None:
        """Обработка команды /start"""
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)

            if user is not None:
                # Пользователь уже существует
                if from_button:
                    message = "✅ Вы уже зарегистрированы! Вот ваш профиль:"
                else:
                    message = "👋 С возвращением!"

                self.show_user_profile(user_id)
                self.send_message(user_id, message,
                                  keyboard=self.keyboards['main'])
            else:
                # Новый пользователь
                if from_button:
                    # Начинаем процесс регистрации
                    self.state_manager.set_state(user_id, "fill_missing_fields")
                    # Инициализируем данные состояния
                    user_data = {field: None for field in self.FIELD_NAMES_RU.keys()}
                    self.state_manager.set_data(user_id, **user_data)
                    # Запрашиваем первое поле
                    self._ask_next_field(user_id, user_data)
                else:
                    # Показываем приветственное сообщение
                    welcome_message = (
                        "👋 Привет! Я бот для знакомств VKinder.\n\n"
                        "Я помогу вам найти интересных людей для общения.\n\n"
                        "Для начала работы нажмите кнопку 'Старт' ниже 👇"
                    )
                    self.send_message(user_id, welcome_message,
                                      keyboard=self.keyboards['welcome'])

    def show_user_profile(self, user_id: int) -> None:
        """Показ профиля пользователя"""
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if not user:
                # Если пользователь не найден, предлагаем зарегистрироваться
                self.send_message(user_id,
                                  "Вы еще не зарегистрированы!\n"
                                  "Нажмите 'Старт' для начала работы.",
                                  keyboard=self.keyboards['welcome'])
                return

            sex_display = self._format_sex(user.sex)
            vk_link = f"https://vk.com/id{user.vk_id}"

            message = (
                f"👤 Ваш профиль:\n"
                f"Имя: {user.first_name or 'Не указано'} {user.last_name or 'Не указано'}\n"
                f"Ссылка: {vk_link}\n"
                f"Возраст: {user.age or 'Не указано'}\n"
                f"Пол: {sex_display}\n"
                f"Город: {user.city or 'Не указано'}\n"
            )

            self.send_message(user_id, message, keyboard=self.keyboards['main'])

    @state_handler("fill_missing_fields")
    def handle_fill_missing_fields(self, user_id: int, text: str) -> None:
        """Заполнение недостающих полей профиля"""
        user_data = self.state_manager.get_data(user_id) or {}

        if not user_data:
            user_data = {field: None for field in self.FIELD_NAMES_RU.keys()}
            self.state_manager.set_data(user_id, **user_data)

        # Определяем текущее поле для заполнения
        current_field = None
        for field in self.FIELD_NAMES_RU.keys():
            if user_data.get(field) is None:
                current_field = field
                break

        if current_field is None:
            # Все поля заполнены
            self._save_user_profile(user_id, user_data)
            return

        # Обработка ввода
        text = text.strip()

        if not text:
            self.send_message(user_id, "Пожалуйста, введите значение")
            return

        # Валидация и преобразование значений
        if current_field == 'sex':
            sex_value = self._parse_sex_input(text)
            if sex_value is None:
                self.send_message(user_id,
                                  "Пожалуйста, укажите пол правильно: 'женский' или 'мужской'")
                return
            user_data[current_field] = sex_value

        elif current_field == 'age':
            try:
                age = int(text)
                if not (14 <= age <= 100):
                    self.send_message(user_id,
                                      "Пожалуйста, укажите корректный возраст (14-100 лет)")
                    return
                user_data[current_field] = age
            except ValueError:
                self.send_message(user_id, "Пожалуйста, укажите возраст цифрами")
                return
        else:
            user_data[current_field] = text

        # Сохраняем данные
        self.state_manager.set_data(user_id, **user_data)

        # Запрашиваем следующее поле
        self._ask_next_field(user_id, user_data)

    def _parse_sex_input(self, text: str) -> Optional[int]:
        """Парсинг ввода пола"""
        text_lower = text.lower()
        sex_mapping = {
            "женский": 1, "ж": 1, "female": 1, "f": 1, "1": 1,
            "мужской": 2, "м": 2, "male": 2, "m": 2, "2": 2
        }
        return sex_mapping.get(text_lower)

    def _ask_next_field(self, user_id: int, user_data: Dict) -> None:
        """Запрос следующего поля для заполнения"""
        missing_fields = [f for f in self.FIELD_NAMES_RU.keys()
                          if user_data.get(f) is None]

        if not missing_fields:
            self._save_user_profile(user_id, user_data)
            return

        next_field = missing_fields[0]
        field_name = self.FIELD_NAMES_RU.get(next_field, next_field)

        if next_field == 'sex':
            prompt = "Укажите ваш пол (мужской/женский):"
        elif next_field == 'age':
            prompt = "Укажите ваш возраст:"
        elif next_field == 'city':
            prompt = "Укажите ваш город:"
        else:
            prompt = f"Пожалуйста, укажите {field_name}:"

        self.send_message(user_id, prompt)

    def _save_user_profile(self, user_id: int, user_data: Dict) -> None:
        """Сохранение профиля пользователя"""
        with Session() as session:
            save_user_from_vk(
                session,
                vk_id=user_id,
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                age=user_data["age"],
                sex=user_data["sex"],
                city=user_data["city"]
            )

        welcome_message = (
            "🎉 Поздравляем! Ваш профиль успешно создан!\n\n"
            "Теперь вы можете использовать все возможности бота:\n"
            "• 🔍 Поиск - для поиска новых знакомств\n"
            "• ❤️ Избранное - для сохранения понравившихся анкет\n"
            "• ⚙️ Настройки - для настройки параметров поиска\n"
            "• ❓ Помощь - если возникнут вопросы"
        )

        self.show_user_profile(user_id)
        self.state_manager.clear_state(user_id)
        self.send_message(user_id, welcome_message,
                          keyboard=self.keyboards['main'])

    def show_next_profile(self, user_id: int) -> None:
        """Показать следующую анкету"""
        with Session() as session:
            profile = get_next_search_profile(session, user_id)

            if not profile:
                self.send_message(user_id,
                                  "Все доступные анкеты просмотрены!\n"
                                  "Попробуйте:\n"
                                  "• Изменить параметры поиска в настройках\n"
                                  "• Начать новый поиск",
                                  keyboard=self.keyboards['main'])
                return

            sex_display = self._format_sex(profile.sex)

            # Получаем фотографии через VKSearcher
            photos = self.vk_searcher.get_user_photos(profile.vk_id)

            # Сохраняем фото в БД
            if photos:
                add_photos_to_profile(session, profile.id, photos)

            # Формируем attachments
            attachments = []
            for photo in photos[:3]:  # Берем до 3 фото
                if 'owner_id' in photo and 'id' in photo:
                    attachments.append(f"photo{photo['owner_id']}_{photo['id']}")

            # Формируем сообщение
            message = f"👤 {profile.first_name} {profile.last_name}\n"
            message += f"🔗 Ссылка: {profile.profile_url}\n"
            if profile.age:
                message += f"📅 Возраст: {profile.age} лет\n"
            message += f"⚧️ Пол: {sex_display}\n"
            if profile.city:
                message += f"📍 Город: {profile.city}\n"
            message += f"\nВыберите действие:"

            if attachments:
                attachment_str = ','.join(attachments)
                self.send_message(user_id, message,
                                  keyboard=self.keyboards['viewing'],
                                  attachment=attachment_str)
            else:
                message += "\nФотографии отсутствуют"
                self.send_message(user_id, message,
                                  keyboard=self.keyboards['viewing'])

            # Добавляем в просмотренные
            user = get_bot_user_by_vk_id(session, user_id)
            if user:
                add_to_viewed_profiles(session, user.id, profile.id)

    def show_favorites(self, user_id: int) -> None:
        """Показать избранные анкеты"""
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if not user:
                self.send_message(user_id, "Сначала заполните профиль!",
                                  keyboard=self.keyboards['main'])
                return

            favorites = get_favorites(session, user.id)
            if not favorites:
                self.send_message(user_id, "У вас пока нет избранных анкет.",
                                  keyboard=self.keyboards['main'])
                return

            message = f"❤️ Ваши избранные ({len(favorites)} анкет):\n\n"
            for i, profile in enumerate(favorites, 1):
                sex_display = self._format_sex(profile.sex)
                message += f"{i}. {profile.first_name} {profile.last_name}\n"
                message += f"   {profile.profile_url}\n"
                if profile.age:
                    message += f"   📅 Возраст: {profile.age} лет\n"
                message += f"   ⚧️ Пол: {sex_display}\n"
                if profile.city:
                    message += f"   📍 Город: {profile.city}\n"
                message += "\n"

            # Разбиваем длинное сообщение
            messages = self._split_long_message(message)
            for msg_part in messages:
                self.send_message(user_id, msg_part,
                                  keyboard=self.keyboards['main'])

    def add_to_favorites_handler(self, user_id: int) -> None:
        """Добавить текущий профиль в избранное"""
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if not user:
                self.send_message(user_id, "Ошибка: пользователь не найден",
                                  keyboard=self.keyboards['main'])
                return

            # Получаем последний просмотренный профиль
            last_viewed = session.query(ViewedProfiles).filter(
                ViewedProfiles.bot_user_id == user.id
            ).order_by(ViewedProfiles.viewed_at.desc()).first()

            if not last_viewed:
                self.send_message(user_id, "Нет профиля для добавления в избранное",
                                  keyboard=self.keyboards['main'])
                return

            profile = last_viewed.profile

            # Проверяем, не добавлен ли уже
            if is_in_favorites(session, user.id, profile.id):
                self.send_message(user_id, "Этот профиль уже в избранном!",
                                  keyboard=self.keyboards['viewing'])
                return

            # Добавляем в избранное
            add_to_favorites(session, user.id, profile.id)
            self.send_message(user_id,
                              f"✅ {profile.first_name} {profile.last_name} добавлен(а) в избранное!",
                              keyboard=self.keyboards['viewing'])

    def add_to_blacklist_handler(self, user_id: int) -> None:
        """Добавить текущий профиль в черный список"""
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if not user:
                self.send_message(user_id, "Ошибка: пользователь не найден",
                                  keyboard=self.keyboards['main'])
                return

            # Получаем последний просмотренный профиль
            last_viewed = session.query(ViewedProfiles).filter(
                ViewedProfiles.bot_user_id == user.id
            ).order_by(ViewedProfiles.viewed_at.desc()).first()

            if not last_viewed:
                self.send_message(user_id, "Нет профиля для добавления в черный список",
                                  keyboard=self.keyboards['main'])
                return

            profile = last_viewed.profile

            # Проверяем, не добавлен ли уже
            if is_in_blacklist(session, user.id, profile.id):
                self.send_message(user_id, "Этот профиль уже в черном списке!",
                                  keyboard=self.keyboards['viewing'])
                return

            # Добавляем в черный список
            add_to_blacklist(session, user.id, profile.id)
            self.send_message(user_id,
                              f"👎 {profile.first_name} {profile.last_name} добавлен(а) в черный список!",
                              keyboard=self.keyboards['viewing'])

            # После добавления в черный список показываем следующий профиль
            self.show_next_profile(user_id)

    def handle_settings(self, user_id: int, text: str = "") -> None:
        """Настройки поиска"""
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if not user:
                self.send_message(user_id, "Сначала заполните профиль!",
                                  keyboard=self.keyboards['main'])
                return

            text_lower = text.lower()

            if text_lower == "настройки":
                # Показываем текущие настройки
                prefs = get_search_preferences(session, user.id)
                if prefs:
                    message = (
                        "⚙️ Ваши текущие настройки поиска:\n\n"
                        f"• Минимальный возраст: {prefs.search_age_min if prefs.search_age_min else '18 (по умолчанию)'}\n"
                        f"• Максимальный возраст: {prefs.search_age_max if prefs.search_age_max else '45 (по умолчанию)'}\n"
                        f"• Город: {prefs.search_city if prefs.search_city else user.city if user.city else 'не установлен'}\n"
                        f"• Пол: {self._format_sex(prefs.search_sex) if prefs.search_sex is not None else 'любой'}\n\n"
                        "Используйте кнопки ниже для изменения настроек:"
                    )
                else:
                    message = (
                        "⚙️ Настройки поиска не установлены.\n\n"
                        f"Текущие значения по умолчанию:\n"
                        f"• Возраст: 18-45 лет\n"
                        f"• Город: {user.city if user.city else 'не установлен'}\n"
                        f"• Пол: любой\n\n"
                        "Используйте кнопки ниже для установки настроек:"
                    )
                self.send_message(user_id, message,
                                  keyboard=self.keyboards['settings'])
                self.state_manager.set_state(user_id, "settings")
                return

            # Обработка кнопок изменения настроек
            if text_lower == "изменить возраст":
                self.send_message(user_id,
                                  "Введите возраст в формате 'от-до', например: 25-35")
                self.state_manager.set_state(user_id, "waiting_for_age")
                return

            if text_lower == "изменить город":
                self.send_message(user_id,
                                  "Введите название города для поиска:")
                self.state_manager.set_state(user_id, "waiting_for_city")
                return

            if text_lower == "изменить пол":
                self.send_message(user_id,
                                  "Введите пол для поиска:\n• мужской\n• женский\n• любой")
                self.state_manager.set_state(user_id, "waiting_for_sex")
                return

            if text_lower == "назад":
                self.send_message(user_id, "Возвращаемся в главное меню",
                                  keyboard=self.keyboards['main'])
                self.state_manager.clear_state(user_id)
                return

            if text_lower in ["очистить историю", "сбросить поиск"]:
                self.clear_search_history(user_id)
                return

            # Если команда не распознана, показываем настройки снова
            self.handle_settings(user_id, "настройки")

    @state_handler("waiting_for_age")
    def handle_age_input(self, user_id: int, text: str) -> None:
        """Обработка ввода возраста"""
        text_lower = text.lower()

        if text_lower in ["назад", "отмена"]:
            self.send_message(user_id, "Отмена изменения возраста",
                              keyboard=self.keyboards['settings'])
            self.state_manager.set_state(user_id, "settings")
            return

        try:
            if "-" in text:
                min_age, max_age = text.split("-")
                min_age = int(min_age.strip())
                max_age = int(max_age.strip())

                if min_age < 18:
                    self.send_message(user_id,
                                      "❌ Минимальный возраст не может быть меньше 18 лет. Попробуйте снова:",
                                      keyboard=self.keyboards['settings'])
                    return
                if max_age > 99:
                    self.send_message(user_id,
                                      "❌ Максимальный возраст не может быть больше 99 лет. Попробуйте снова:",
                                      keyboard=self.keyboards['settings'])
                    return
                if min_age > max_age:
                    self.send_message(user_id,
                                      "❌ Минимальный возраст не может быть больше максимального. Попробуйте снова:",
                                      keyboard=self.keyboards['settings'])
                    return

                with Session() as session:
                    user = get_bot_user_by_vk_id(session, user_id)
                    if user:
                        create_or_update_search_preferences(
                            session,
                            user.id,
                            search_age_min=min_age,
                            search_age_max=max_age
                        )
                        self.send_message(user_id,
                                          f"✅ Возраст поиска установлен: {min_age}-{max_age} лет",
                                          keyboard=self.keyboards['settings'])
                        self.state_manager.set_state(user_id, "settings")
                    else:
                        self.send_message(user_id, "❌ Пользователь не найден",
                                          keyboard=self.keyboards['main'])
                        self.state_manager.clear_state(user_id)
            else:
                self.send_message(user_id,
                                  "❌ Неправильный формат. Используйте формат: от-до, например: 25-35",
                                  keyboard=self.keyboards['settings'])
        except (ValueError, IndexError):
            self.send_message(user_id,
                              "❌ Неправильный формат возраста. Используйте формат: от-до, например: 25-35",
                              keyboard=self.keyboards['settings'])

    @state_handler("waiting_for_city")
    def handle_city_input(self, user_id: int, text: str) -> None:
        """Обработка ввода города"""
        text_lower = text.lower()

        if text_lower in ["назад", "отмена"]:
            self.send_message(user_id, "Отмена изменения города",
                              keyboard=self.keyboards['settings'])
            self.state_manager.set_state(user_id, "settings")
            return

        if not text.strip():
            self.send_message(user_id,
                              "❌ Название города не может быть пустым. Попробуйте снова:",
                              keyboard=self.keyboards['settings'])
            return

        city = text.strip()
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if user:
                create_or_update_search_preferences(session, user.id, search_city=city)
                self.send_message(user_id, f"✅ Город поиска установлен: {city}",
                                  keyboard=self.keyboards['settings'])
                self.state_manager.set_state(user_id, "settings")
            else:
                self.send_message(user_id, "❌ Пользователь не найден",
                                  keyboard=self.keyboards['main'])
                self.state_manager.clear_state(user_id)

    @state_handler("waiting_for_sex")
    def handle_sex_input(self, user_id: int, text: str) -> None:
        """Обработка ввода пола"""
        text_lower = text.lower()

        if text_lower in ["назад", "отмена"]:
            self.send_message(user_id, "Отмена изменения пола",
                              keyboard=self.keyboards['settings'])
            self.state_manager.set_state(user_id, "settings")
            return

        sex_mapping = {
            "женский": 1, "ж": 1, "female": 1, "f": 1,
            "мужской": 2, "м": 2, "male": 2, "m": 2,
            "любой": 0, "любой пол": 0
        }
        sex_value = sex_mapping.get(text_lower)

        if sex_value is None:
            self.send_message(user_id,
                              "❌ Неправильное значение пола. Используйте: мужской, женский или любой",
                              keyboard=self.keyboards['settings'])
            return

        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if user:
                create_or_update_search_preferences(session, user.id, search_sex=sex_value)
                sex_display = self._format_sex(search_sex)
                self.send_message(user_id,
                                  f"✅ Пол для поиска установлен: {sex_display}",
                                  keyboard=self.keyboards['settings'])
                self.state_manager.set_state(user_id, "settings")
            else:
                self.send_message(user_id, "❌ Пользователь не найден",
                                  keyboard=self.keyboards['main'])
                self.state_manager.clear_state(user_id)

    def start_search(self, user_id: int) -> None:
        """Поиск"""
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if not user:
                self.send_message(user_id,
                                  "Сначала нужно зарегистрироваться!\n"
                                  "Нажмите 'Старт' для начала работы.",
                                  keyboard=self.keyboards['welcome'])
                return

            # Получаем настройки поиска
            prefs = get_search_preferences(session, user.id)

            # Используем настройки или данные пользователя по умолчанию
            search_city = prefs.search_city if prefs and prefs.search_city else user.city or ""
            search_age_min = prefs.search_age_min if prefs and prefs.search_age_min else 18
            search_age_max = prefs.search_age_max if prefs and prefs.search_age_max else 45
            search_sex = prefs.search_sex if prefs and prefs.search_sex is not None else 0

            # Информируем пользователя о параметрах поиска
            sex_display = self._format_sex(search_sex)
            city_display = search_city if search_city else "любой"

            info_msg = (
                f"🔎 Начинаю поиск с параметрами:\n\n"
                f"📍 Город: {city_display}\n"
                f"📅 Возраст: {search_age_min}-{search_age_max} лет\n"
                f"⚧️ Пол: {sex_display}\n\n"
                f"Поиск может занять несколько секунд..."
            )
            self.send_message(user_id, info_msg)

            logger.info(f"=== НАЧАЛО ПОИСКА ===")
            logger.info(f"Пользователь: {user.first_name} {user.last_name}")
            logger.info(f"Параметры: город='{search_city}', возраст={search_age_min}-{search_age_max}, пол={search_sex}")

            try:
                # Используем умный поиск
                found_users = self.vk_searcher.smart_search_users(
                    city=search_city,
                    age_from=search_age_min,
                    age_to=search_age_max,
                    sex=search_sex,
                    target_count=1050
                )

                logger.info(f"Умный поиск нашел {len(found_users)} пользователей")

                if not found_users:
                    # Пробуем альтернативные стратегии
                    logger.info("Пробуем альтернативные стратегии поиска...")

                    # Стратегия 1: Без города
                    if search_city:
                        found_users = self.vk_searcher.smart_search_users(
                            city="",
                            age_from=search_age_min,
                            age_to=search_age_max,
                            sex=search_sex,
                            target_count=30
                        )
                        logger.info(f"Поиск без города нашел {len(found_users)} пользователей")

                    # Стратегия 2: Расширенный возраст
                    if not found_users:
                        found_users = self.vk_searcher.smart_search_users(
                            city=search_city,
                            age_from=max(18, search_age_min - 5),
                            age_to=min(99, search_age_max + 5),
                            sex=search_sex,
                            target_count=30
                        )
                        logger.info(f"Расширенный возраст нашел {len(found_users)} пользователей")

                    # Стратегия 3: Любой пол
                    if not found_users and search_sex != 0:
                        found_users = self.vk_searcher.smart_search_users(
                            city=search_city,
                            age_from=search_age_min,
                            age_to=search_age_max,
                            sex=0,
                            target_count=30
                        )
                        logger.info(f"Любой пол нашел {len(found_users)} пользователей")

                if not found_users:
                    self.send_message(user_id,
                                      "❌ Не удалось найти подходящих пользователей.\n\n"
                                      "Возможные причины:\n"
                                      "• В выбранном городе мало открытых профилей\n"
                                      "• Параметры поиска слишком строгие\n"
                                      "• Проблемы с подключением к VK\n\n"
                                      "Попробуйте:\n"
                                      "1. Изменить город в настройках\n"
                                      "2. Расширить возрастной диапазон\n"
                                      "3. Попробовать позже",
                                      keyboard=self.keyboards['main'])
                    return

                # Сохраняем результаты
                saved_profiles = save_search_results(session,found_users)

                if saved_profiles:
                    success_msg = (
                        f"✅ Поиск завершен!\n"
                        f"Найдено анкет: {len(saved_profiles)}\n"
                        f"Показываю первую..."
                    )
                    self.send_message(user_id, success_msg,
                                      keyboard=self.keyboards['viewing'])

                    # Показываем первый профиль
                    self.show_next_profile(user_id)
                else:
                    self.send_message(user_id, "Не удалось сохранить результаты поиска",
                                      keyboard=self.keyboards['main'])

            except Exception as e:
                logger.error(f"Ошибка при поиске: {e}", exc_info=True)
                self.send_message(user_id,
                                  "⚠️ Произошла ошибка при поиске.\n"
                                  "Попробуйте изменить параметры или повторить позже.",
                                  keyboard=self.keyboards['main'])

    def clear_search_history(self, user_id: int) -> None:
        """Очистить историю поиска"""
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if user:
                # Удаляем записи из черного списка
                session.query(Blacklist).filter(
                    Blacklist.bot_user_id == user.id
                ).delete()

                # Очищаем таблицу viewed_profiles
                try:
                    session.query(ViewedProfiles).filter(
                        ViewedProfiles.bot_user_id == user.id
                    ).delete()
                except Exception:
                    pass  # Таблица может не существовать

                session.commit()

                self.send_message(user_id,
                                  "✅ История поиска очищена!\n"
                                  "Теперь вы сможете увидеть ранее показанные анкеты снова.",
                                  keyboard=self.keyboards['main'])
            else:
                self.send_message(user_id, "Пользователь не найден",
                                  keyboard=self.keyboards['main'])

    def handle_message(self, user_id: int, text: str) -> None:
        """Обработка входящего сообщения"""
        logger.info(f"Новое сообщение от {user_id}: {text}")

        try:
            text_lower = text.lower().strip()

            # Обработка команды /start и кнопки Старт
            if any(cmd in text_lower for cmd in self.COMMANDS["start"]) or text_lower == "старт":
                self.state_manager.clear_state(user_id)
                self.handle_start_command(user_id, from_button=(text_lower == "старт"))
                return

            # Проверяем текущее состояние ДО обработки других команд
            current_state = self.state_manager.get_state(user_id)

            # Обработка состояний ДО всех остальных команд
            if current_state in self.state_handlers:
                self.state_handlers[current_state](user_id, text)
                return

            # Проверяем, зарегистрирован ли пользователь
            with Session() as session:
                user = get_bot_user_by_vk_id(session, user_id)
                if not user:
                    # Если пользователь не зарегистрирован, предлагаем начать
                    welcome_message = (
                        "👋 Вы еще не зарегистрированы!\n\n"
                        "Чтобы начать пользоваться ботом, нажмите кнопку 'Старт' или напишите /start"
                    )
                    self.send_message(user_id, welcome_message,
                                      keyboard=self.keyboards['welcome'])
                    return

            # Обработка команд главного меню
            if text_lower == "поиск":
                self.start_search(user_id)
                return

            if text_lower == "избранное":
                self.show_favorites(user_id)
                return

            if text_lower == "помощь":
                help_text = (
                    "🤖 Помощь по командам:\n\n"
                    "🎯 Основные команды:\n"
                    "• Старт - Начать работу с ботом\n"
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
                self.send_message(user_id, help_text,
                                  keyboard=self.keyboards['main'])
                return

            # Обработка команд во время просмотра
            if any(cmd in text_lower for cmd in self.COMMANDS["next"]):
                self.show_next_profile(user_id)
                return

            if any(cmd in text_lower for cmd in self.COMMANDS["like"]):
                self.add_to_favorites_handler(user_id)
                return

            if any(cmd in text_lower for cmd in self.COMMANDS["dislike"]):
                self.add_to_blacklist_handler(user_id)
                return

            if any(cmd in text_lower for cmd in self.COMMANDS["menu"]):
                with Session() as session:
                    user = get_bot_user_by_vk_id(session, user_id)
                    if user:
                        self.send_message(user_id, "🏠 Возвращаемся в главное меню",
                                          keyboard=self.keyboards['main'])
                    else:
                        self.send_message(user_id, "🏠 Возвращаемся в начало",
                                          keyboard=self.keyboards['welcome'])
                self.state_manager.clear_state(user_id)
                return

            # Обработка настроек
            if text_lower == "настройки":
                self.handle_settings(user_id, "настройки")
                return

            # Обработка команд из клавиатуры настроек
            if text_lower == "изменить возраст":
                self.handle_settings(user_id, "изменить возраст")
                return

            if text_lower == "изменить город":
                self.handle_settings(user_id, "изменить город")
                return

            if text_lower == "изменить пол":
                self.handle_settings(user_id, "изменить пол")
                return

            if text_lower == "очистить историю":
                self.clear_search_history(user_id)
                return

            # Обработка команды "назад"
            if text_lower == "назад":
                self.send_message(user_id, "Возвращаемся в главное меню",
                                  keyboard=self.keyboards['main'])
                self.state_manager.clear_state(user_id)
                return

            # Если команда не распознана
            self.send_message(user_id,
                              "Не понял команду. Напишите 'Помощь' для списка команд.",
                              keyboard=self.keyboards['main'])

        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения от {user_id}: {e}",
                         exc_info=True)
            self.send_message(user_id,
                              "⚠️ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте еще раз.",
                              keyboard=self.keyboards['main'])

    def run(self) -> None:
        """Запуск бота"""
        logger.info("Бот запущен")

        try:
            for event in self.longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    request = event.text
                    user_id = event.user_id
                    if user_id and request:
                        try:
                            self.handle_message(user_id, request)
                        except Exception as e:
                            logger.error(f"Ошибка в обработке сообщения: {e}",
                                         exc_info=True)
                            try:
                                self.send_message(user_id,
                                                  "⚠️ Произошла внутренняя ошибка. Пожалуйста, попробуйте позже.",
                                                  keyboard=self.keyboards['main'])
                            except Exception as e2:
                                logger.error(f"Ошибка отправки сообщения об ошибке: {e2}")
        except KeyboardInterrupt:
            logger.info("Бот остановлен пользователем")
        except Exception as e:
            logger.error(f"Критическая ошибка в работе бота: {e}", exc_info=True)