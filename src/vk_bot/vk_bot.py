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
    create_or_update_search_preferences,
    get_search_preferences,
    add_photos_to_profile,
    get_favorites,
    is_in_favorites,
    is_in_blacklist,
    add_to_blacklist
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

    def __init__(self, group_token: str, user_token: str) -> None:
        self.__group_token = group_token
        self.__user_token = user_token

        # Проверяем токены
        self._validate_tokens()

        self.vk_session = VkApi(token=self.__group_token)
        self.longpoll = VkLongPoll(self.vk_session)
        self.vk = self.vk_session.get_api()

        # Инициализируем VKSearcher с пользовательским токеном
        self.vk_searcher = VKSearcher(self.__user_token)

        # Инициализируем клавиатуры
        self.keyboard = VkBotKeyboards.create_main_keyboard()
        self.search_keyboard = VkBotKeyboards.create_search_keyboard()
        self.viewing_keyboard = VkBotKeyboards.create_viewing_keyboard()
        self.settings_keyboard = VkBotKeyboards.create_settings_keyboard()

        self.state_manager = StateManager()
        self.state_handlers: Dict[str, Callable] = self._collect_state_handlers()

        # Тест соединения после инициализации всех компонентов бота
        self.test_connection()

    def _validate_tokens(self):
        # Проверяем валидность токенов
        logger.info("Проверка токенов...")

        if not self.__group_token or self.__group_token == "your_group_token_here":
            logger.error("Групповой токен не установлен или имеет значение по умолчанию!")
            raise ValueError("Групповой токен не установлен. Проверьте .env файл")

        if not self.__user_token or self.__user_token == "your_user_token_here":
            logger.error("Пользовательский токен не установлен или имеет значение по умолчанию!")
            raise ValueError("Пользовательский токен не установлен. Проверьте .env файл")

        # Проверяем формат токенов
        if len(self.__group_token) < 20:
            logger.warning(f"Групповой токен слишком короткий: {len(self.__group_token)} символов")

        if len(self.__user_token) < 20:
            logger.warning(f"Пользовательский токен слишком короткий: {len(self.__user_token)} символов")

        logger.info("Токены прошли базовую проверку")

    def _collect_state_handlers(self) -> dict:
        handlers = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, "state_name"):
                handlers[attr.state_name] = attr
        return handlers

    def send_msg(self, user_id: int, message: str, keyboard: Optional[VkKeyboard] = None,
                 attachment: Optional[str] = None):
        params = {
            "user_id": user_id,
            "message": message,
            "random_id": get_random_id()
        }
        if keyboard:
            params["keyboard"] = keyboard.get_keyboard()
        if attachment:
            params["attachment"] = attachment

        self.vk.messages.send(**params)
        logger.info(f"Отправлено сообщение пользователю {user_id}: {message}")

    def _format_sex(self, sex_value) -> str:
        # Преобразуем значение пола в стоку
        if sex_value is None:
            return "Не указан"
        if isinstance(sex_value, str):
            # Если уже строка, пытаемся преобразовать
            sex_lower = sex_value.lower()
            if sex_lower in ["женский", "female", "f", "1"]:
                return "Женский"
            elif sex_lower in ["мужской", "male", "m", "2"]:
                return "Мужской"
            else:
                return sex_value  # возвращаем как есть
        elif isinstance(sex_value, int):
            if sex_value == 1:
                return "Женский"
            elif sex_value == 2:
                return "Мужской"
            else:
                return "Не указан"
        return "Не указан"

    def show_user_profile(self, user_id: int):
        # Показываем профиль пользователя
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if not user:
                self.send_msg(user_id, "Профиль не найден. Начните с команды /start")
                return

            # Проверяем, какие атрибуты есть у пользователя
            first_name = getattr(user, 'first_name', 'Не указано')
            last_name = getattr(user, 'last_name', 'Не указано')
            age = getattr(user, 'age', 'Не указано')
            city = getattr(user, 'city', 'Не указано')

            # Проверяем возможные названия поля для ссылки
            vk_link = getattr(user, 'vk_link', None)
            if not vk_link:
                vk_link = getattr(user, 'link', None)
            if not vk_link:
                vk_link = getattr(user, 'profile_url', None)
            if not vk_link:
                vk_link = 'Не указано'

            sex_display = self._format_sex(getattr(user, 'sex', None))

            message = (
                f"👤 Ваш профиль:\n"
                f"Имя: {first_name} {last_name}\n"
                f"Ссылка: {vk_link}\n"
                f"Возраст: {age}\n"
                f"Пол: {sex_display}\n"
                f"Город: {city}\n"
            )
            self.send_msg(user_id, message, keyboard=self.keyboard)

    def show_next_profile(self, user_id: int):
        # Функция для показа следующего найденного профиля
        with Session() as session:
            profile = get_next_search_profile(session, user_id)
            if not profile:
                self.send_msg(user_id, "Больше нет анкет для просмотра!", keyboard=self.keyboard)
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
            message += f"🔗 {profile.profile_url}\n"
            if profile.age:
                message += f"🎂 {profile.age} лет\n"
            message += f"👫 Пол: {sex_display}\n"
            if profile.city:
                message += f"📍 {profile.city}\n"

            if attachments:
                attachment_str = ','.join(attachments)
                self.send_msg(user_id, message, keyboard=self.viewing_keyboard,
                              attachment=attachment_str)
            else:
                message += "\n📸 Фотографии отсутствуют"
                self.send_msg(user_id, message, keyboard=self.viewing_keyboard)

            # Добавляем в просмотренные
            user = get_bot_user_by_vk_id(session, user_id)
            if user:
                add_to_viewed(session, user.id, profile.id)

    def show_favorites(self, user_id: int):
        # Показать избранные анкеты
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
                sex_display = self._format_sex(profile.sex)
                message += f"{i}. {profile.first_name} {profile.last_name}\n"
                message += f"   {profile.profile_url}\n"
                if profile.age:
                    message += f"   Возраст: {profile.age} лет\n"
                message += f"   Пол: {sex_display}\n"
                if profile.city:
                    message += f"   Город: {profile.city}\n"
                message += "\n"

            self.send_msg(user_id, message, keyboard=self.keyboard)

    def add_to_favorites_handler(self, user_id: int):
        # Добавить текущий профиль в избранное
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if not user:
                self.send_msg(user_id, "Ошибка: пользователь не найден", keyboard=self.keyboard)
                return

            # Получаем последний просмотренный профиль
            profile = get_next_search_profile(session, user_id)
            if not profile:
                self.send_msg(user_id, "Нет профиля для добавления в избранное", keyboard=self.keyboard)
                return

            # Проверяем, не добавлен ли уже
            if is_in_favorites(session, user.id, profile.id):
                self.send_msg(user_id, "Этот профиль уже в избранном!", keyboard=self.viewing_keyboard)
                return

            # Добавляем в избранное
            add_to_favorites(session, user.id, profile.id)
            self.send_msg(user_id, f"✅ {profile.first_name} {profile.last_name} добавлен(а) в избранное!",
                          keyboard=self.viewing_keyboard)

    def add_to_blacklist_handler(self, user_id: int):
        # Добавить текущий профиль в черный список
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if not user:
                self.send_msg(user_id, "Ошибка: пользователь не найден", keyboard=self.keyboard)
                return

            # Получаем последний просмотренный профиль
            profile = get_next_search_profile(session, user_id)
            if not profile:
                self.send_msg(user_id, "Нет профиля для добавления в черный список", keyboard=self.keyboard)
                return

            # Проверяем, не добавлен ли уже
            if is_in_blacklist(session, user.id, profile.id):
                self.send_msg(user_id, "Этот профиль уже в черном списке!", keyboard=self.viewing_keyboard)
                return

            # Добавляем в черный список
            add_to_blacklist(session, user.id, profile.id)
            self.send_msg(user_id, f"👎 {profile.first_name} {profile.last_name} добавлен(а) в черный список!",
                          keyboard=self.viewing_keyboard)

            # После добавления в черный список показываем следующий профиль
            self.show_next_profile(user_id)

    @state_handler("fill_missing_fields")
    def handle_fill_missing_fields(self, user_id: int, text: str):
        user_data = self.state_manager.get_data(user_id) or {}
        required_fields = ["first_name", "last_name", "vk_link", "age", "sex", "city"]

        # Определяем, какое поле заполняем
        current_field = None
        for field in required_fields:
            if not user_data.get(field):
                current_field = field
                break

        if current_field == 'sex':
            # Преобразуем текстовый ввод в числовое значение
            text_lower = text.strip().lower()
            sex_mapping = {
                "женский": 1,
                "ж": 1,
                "female": 1,
                "f": 1,
                "1": 1,
                "мужской": 2,
                "м": 2,
                "male": 2,
                "m": 2,
                "2": 2
            }
            sex_value = sex_mapping.get(text_lower)
            if sex_value is None:
                self.send_msg(user_id, "Пожалуйста, укажите пол правильно: 'женский' или 'мужской'")
                return
            user_data[current_field] = sex_value
        else:
            # Для остальных полей сохраняем как есть
            user_data[current_field] = text.strip()

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

    def handle_settings(self, user_id: int, text: str = ""):
        # Настройки поиска
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if not user:
                self.send_msg(user_id, "Сначала заполните профиль!", keyboard=self.keyboard)
                return

            text_lower = text.lower()

            if text_lower == "настройки":
                # Показываем текущие настройки
                prefs = get_search_preferences(session, user.id)
                if prefs:
                    # Проверяем, какие атрибуты есть у объекта
                    min_age = getattr(prefs, 'min_age', getattr(prefs, 'age_from', None))
                    max_age = getattr(prefs, 'max_age', getattr(prefs, 'age_to', None))
                    city = getattr(prefs, 'city', None)
                    sex = getattr(prefs, 'sex', None)

                    message = (
                        "⚙️ Ваши текущие настройки поиска:\n\n"
                        f"• Минимальный возраст: {min_age or 'не установлен'}\n"
                        f"• Максимальный возраст: {max_age or 'не установлен'}\n"
                        f"• Город: {city or 'не установлен'}\n"
                        f"• Пол: {self._format_sex(sex) if sex is not None else 'любой'}\n\n"
                        "Используйте кнопки ниже для изменения настроек:"
                    )
                else:
                    message = (
                        "⚙️ Настройки поиска не установлены.\n\n"
                        "Используйте кнопки ниже для установки настроек:"
                    )
                self.send_msg(user_id, message, keyboard=self.settings_keyboard)
                self.state_manager.set_state(user_id, "settings")
                return

            # Обработка кнопок изменения настроек
            if text_lower == "изменить возраст":
                self.send_msg(user_id, "Введите возраст в формате 'от-до', например: 25-35")
                self.state_manager.set_state(user_id, "waiting_for_age")
                return

            if text_lower == "изменить город":
                self.send_msg(user_id, "Введите название города для поиска:")
                self.state_manager.set_state(user_id, "waiting_for_city")
                return

            if text_lower == "изменить пол":
                self.send_msg(user_id, "Введите пол для поиска:\n• мужской\n• женский\n• любой")
                self.state_manager.set_state(user_id, "waiting_for_sex")
                return

            if text_lower == "назад":
                self.send_msg(user_id, "Возвращаемся в главное меню", keyboard=self.keyboard)
                self.state_manager.clear_state(user_id)
                return

            # Если команда не распознана, показываем настройки снова
            self.handle_settings(user_id, "настройки")

    @state_handler("waiting_for_age")
    def handle_age_input(self, user_id: int, text: str):
        # Обработка ввода возраста
        text_lower = text.lower()

        if text_lower == "назад" or text_lower == "отмена":
            self.send_msg(user_id, "Отмена изменения возраста", keyboard=self.settings_keyboard)
            self.state_manager.set_state(user_id, "settings")
            return

        try:
            if "-" in text:
                min_age, max_age = text.split("-")
                min_age = int(min_age.strip())
                max_age = int(max_age.strip())

                if min_age < 18:
                    self.send_msg(user_id, "❌ Минимальный возраст не может быть меньше 18 лет. Попробуйте снова:",
                                  keyboard=self.settings_keyboard)
                    return
                if max_age > 99:
                    self.send_msg(user_id, "❌ Максимальный возраст не может быть больше 99 лет. Попробуйте снова:",
                                  keyboard=self.settings_keyboard)
                    return
                if min_age > max_age:
                    self.send_msg(user_id, "❌ Минимальный возраст не может быть больше максимального. Попробуйте снова:",
                                  keyboard=self.settings_keyboard)
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
                        self.send_msg(user_id, f"✅ Возраст поиска установлен: {min_age}-{max_age} лет",
                                      keyboard=self.settings_keyboard)
                        self.state_manager.set_state(user_id, "settings")
                    else:
                        self.send_msg(user_id, "❌ Пользователь не найден", keyboard=self.keyboard)
                        self.state_manager.clear_state(user_id)
            else:
                self.send_msg(user_id, "❌ Неправильный формат. Используйте формат: от-до, например: 25-35",
                              keyboard=self.settings_keyboard)
        except (ValueError, IndexError):
            self.send_msg(user_id, "❌ Неправильный формат возраста. Используйте формат: от-до, например: 25-35",
                          keyboard=self.settings_keyboard)

    @state_handler("waiting_for_city")
    def handle_city_input(self, user_id: int, text: str):
        # Обработка ввода города
        text_lower = text.lower()

        if text_lower == "назад" or text_lower == "отмена":
            self.send_msg(user_id, "Отмена изменения города", keyboard=self.settings_keyboard)
            self.state_manager.set_state(user_id, "settings")
            return

        if not text.strip():
            self.send_msg(user_id, "❌ Название города не может быть пустым. Попробуйте снова:",
                          keyboard=self.settings_keyboard)
            return

        city = text.strip()
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if user:
                create_or_update_search_preferences(session, user.id, search_city=city)
                self.send_msg(user_id, f"✅ Город поиска установлен: {city}",
                              keyboard=self.settings_keyboard)
                self.state_manager.set_state(user_id, "settings")
            else:
                self.send_msg(user_id, "❌ Пользователь не найден", keyboard=self.keyboard)
                self.state_manager.clear_state(user_id)

    @state_handler("waiting_for_sex")
    def handle_sex_input(self, user_id: int, text: str):
        # Обработка ввода пола
        text_lower = text.lower()

        if text_lower == "назад" or text_lower == "отмена":
            self.send_msg(user_id, "Отмена изменения пола", keyboard=self.settings_keyboard)
            self.state_manager.set_state(user_id, "settings")
            return

        sex_mapping = {
            "женский": 1,
            "ж": 1,
            "female": 1,
            "f": 1,
            "мужской": 2,
            "м": 2,
            "male": 2,
            "m": 2,
            "любой": 0,
            "любой пол": 0
        }
        sex_value = sex_mapping.get(text_lower)

        if sex_value is None:
            self.send_msg(user_id, "❌ Неправильное значение пола. Используйте: мужской, женский или любой",
                          keyboard=self.settings_keyboard)
            return

        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if user:
                create_or_update_search_preferences(session, user.id, search_sex=sex_value)
                sex_display = self._format_sex(sex_value) if sex_value != 0 else "любой"
                self.send_msg(user_id, f"✅ Пол для поиска установлен: {sex_display}",
                              keyboard=self.settings_keyboard)
                self.state_manager.set_state(user_id, "settings")
            else:
                self.send_msg(user_id, "❌ Пользователь не найден", keyboard=self.keyboard)
                self.state_manager.clear_state(user_id)

    def handle_message(self, user_id: int, text: str):
        logger.info(f"Новое сообщение от {user_id}: {text}")

        text_lower = text.lower()

        # Проверяем текущее состояние
        current_state = self.state_manager.get_state(user_id)

        # Если пользователь в состоянии настроек
        if current_state == "settings":
            self.handle_settings(user_id, text)
            return

        # Если пользователь в состоянии ожидания ввода возраста
        if current_state == "waiting_for_age":
            self.handle_age_input(user_id, text)
            return

        # Если пользователь в состоянии ожидания ввода города
        if current_state == "waiting_for_city":
            self.handle_city_input(user_id, text)
            return

        # Если пользователь в состоянии ожидания ввода пола
        if current_state == "waiting_for_sex":
            self.handle_sex_input(user_id, text)
            return

        # Если пользователь в состоянии заполнения полей
        if current_state == "fill_missing_fields":
            self.handle_fill_missing_fields(user_id, text)
            return

        # Обработка основных команд
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

            # Получаем данные пользователя из VK - используем пользовательский токен для VKUser
            vk_user = VKUser(access_token=self.__user_token, user_id=user_id)
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

        # Обработка команд Избранное
        if text_lower in ["❤️ в избранное", "в избранное", "избранное", "лайк"]:
            self.add_to_favorites_handler(user_id)
            return
        # Обработка команд Черный список
        if text_lower in ["👎 в черный список", "не нравится", "в черный список", "черный список"]:
            self.add_to_blacklist_handler(user_id)
            return
        # Обработка команд В меню
        if text_lower in ["🔙 в меню", "в меню", "меню", "🏠 в меню"]:
            self.send_msg(user_id, "Возвращаемся в главное меню", keyboard=self.keyboard)
            self.state_manager.clear_state(user_id)
            return
        # Обработка команд Помощь
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

        # Обработка команд Настройки
        if text_lower == "настройки":
            self.handle_settings(user_id, "настройки")
            return

        # Обработка команд Назад
        if text_lower == "назад":
            self.send_msg(user_id, "Возвращаемся в главное меню", keyboard=self.keyboard)
            self.state_manager.clear_state(user_id)
            return

        # Если команда не распознана
        self.send_msg(user_id, "Не понял команду. Напишите 'Помощь' для списка команд.", keyboard=self.keyboard)

    def start_search(self, user_id: int):
        # Начало поиска (гибкий поиск)
        with Session() as session:
            user = get_bot_user_by_vk_id(session, user_id)
            if not user:
                self.send_msg(user_id, "Сначала заполните профиль!", keyboard=self.keyboard)
                return

            logger.info("=== ГИБКИЙ ПОИСК ===")

            # Определяем параметры поиска
            search_city = user.city
            search_age_min = 18
            search_age_max = 45  # Расширим возраст

            # Определяем пол для поиска
            if user.sex == 2:  # пользователь мужчина
                search_sex = 1  # ищем женщин
            elif user.sex == 1:  # пользователь женщина
                search_sex = 2  # ищем мужчин
            else:
                search_sex = 0  # любой пол

            # Пробуем разные стратегии поиска (от более узкого к более широкому)
            search_strategies = [
                # Стратегия 1: Точный поиск по городу и полу
                {"city": search_city, "age_from": search_age_min, "age_to": search_age_max,
                 "sex": search_sex, "desc": "Точный поиск в вашем городе"},

                # Стратегия 2: Без пола, только город
                {"city": search_city, "age_from": search_age_min, "age_to": search_age_max,
                 "sex": 0, "desc": "Любой пол в вашем городе"},

                # Стратегия 3: Без города, только пол
                {"city": "", "age_from": search_age_min, "age_to": search_age_max,
                 "sex": search_sex, "desc": "Без города, только нужный пол"},

                # Стратегия 4: Широкий поиск
                {"city": "", "age_from": 18, "age_to": 99,
                 "sex": 0, "desc": "Самый широкий поиск"},
            ]

            found_users = []

            for strategy in search_strategies:
                logger.info(f"Пробуем стратегию: {strategy['desc']}")
                logger.info(f"  Город: {strategy['city']}, Возраст: {strategy['age_from']}-{strategy['age_to']}, Пол: {strategy['sex']}")


                users = self.vk_searcher.search_users(
                    city=strategy['city'],
                    age_from=strategy['age_from'],
                    age_to=strategy['age_to'],
                    sex=strategy['sex'],
                    count=100
                )

                if users:
                    logger.info(f"Стратегия '{strategy['desc']}' нашла {len(users)} пользователей")
                    found_users.extend(users)
                    if len(found_users) >= 10:
                        break
                else:
                    logger.info(f"Стратегия '{strategy['desc']}' не дала результатов")

            logger.info(f"Всего найдено пользователей: {len(found_users)}")

            if not found_users:
                self.send_msg(user_id,
                              "Не удалось найти подходящих пользователей.\n"
                              "Возможные причины:\n"
                              "1. Ваши параметры поиска слишком строгие\n"
                              "2. В вашем городе мало открытых профилей\n"
                              "3. Попробуйте изменить параметры в настройках",
                              keyboard=self.keyboard)
                return

            # Убираем дубликаты
            unique_users = []
            seen_ids = set()
            for user_data in found_users:
                if user_data['vk_id'] not in seen_ids:
                    seen_ids.add(user_data['vk_id'])
                    unique_users.append(user_data)

            logger.info(f"Уникальных пользователей: {len(unique_users)}")

            # Сохраняем результаты
            saved_profiles = save_search_results(session, user.id, unique_users)

            if saved_profiles:
                self.send_msg(user_id, f"Найдено {len(saved_profiles)} анкет! Показываю первую...",
                              keyboard=self.viewing_keyboard)
                self.show_next_profile(user_id)
            else:
                self.send_msg(user_id, "Не удалось сохранить результаты поиска", keyboard=self.keyboard)

    def test_connection(self):
        # Тест подключения к VK API
        logger.info("=== ТЕСТ ПОДКЛЮЧЕНИЯ К VK API ===")

        try:
            # Тест группового токена (бот)
            logger.info("Тестируем групповой токен...")
            group_info = self.vk.groups.getById()
            logger.info(f"✓ Групповой токен работает. Группа: {group_info[0]['name']}")

            # Тест пользовательского токена (поиск) - используем простой запрос
            logger.info("Тестируем пользовательский токен...")
            test_response = self.vk_searcher._make_request('users.get', {'user_ids': 1})

            if test_response:
                logger.info(f"✓ Пользовательский токен работает. Тестовый пользователь получен")
            else:
                logger.error("✗ Пользовательский токен не возвращает данные. Возможно, недостаточно прав или токен невалиден.")

        except Exception as e:
            logger.error(f"✗ Ошибка подключения к VK API: {e}")
            import traceback
            logger.error(f"Детали ошибки: {traceback.format_exc()}")

        logger.info("=== ТЕСТ ПОДКЛЮЧЕНИЯ ЗАВЕРШЕН ===")

    def run(self) -> None:
        logger.info("Бот запущен")
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                request = event.text
                user_id = event.user_id
                if user_id and request:
                    self.handle_message(user_id, request)