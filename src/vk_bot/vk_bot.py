import logging

from typing import Callable, Dict, Optional
from vk_api import VkApi
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
from src.database.crud import get_user_by_vk_id, save_user_from_vk
from src.database.statemanager import StateManager
from src.vk_bot.vk_client import VKUser


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
        "gender": "пол",
        "city": "город"
    }
    
    def __init__(self, token) -> None:
        self.__token = token
        self.vk_session = VkApi(token=self.__token)
        self.longpoll = VkLongPoll(self.vk_session)
        self.vk = self.vk_session.get_api()    
        self.keyboard = self.create_main_keyboard()

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

    def create_main_keyboard(self):
        """Создание основной клавиатуры"""
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button('Поиск', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Избранное', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Настройки', color=VkKeyboardColor.SECONDARY)
        keyboard.add_button('Помощь', color=VkKeyboardColor.SECONDARY)
        return keyboard
    
    def show_user_profile(self, user_id: int):
        user_info = get_user_by_vk_id(user_id)
        if user_info is not None:
            user_data = {
                "first_name": user_info.first_name,
                "last_name": user_info.last_name,
                "age": user_info.age,
                "gender": user_info.gender,
                "city": user_info.city,
                "vk_link": user_info.user_vk_link,
                "vk_id": user_info.vk_user_id
            }
        else:
            # если пользователя нет в базе, берём данные из StateManager
            user_data = self.state_manager.get_data(user_id)

        lines = []
        for key in ["first_name", "last_name", "age", "gender", "city", "vk_link"]:
            field_name = self.FIELD_NAMES_RU.get(key, key)
            value = user_data.get(key) if user_data else None
            if value is None or (isinstance(value, str) and not value.strip()):
                value = "не указан"
            lines.append(f"{field_name.capitalize()}: {value}")

        message = "Ваша анкета:\n\n" + "\n".join(lines)
        self.send_msg(user_id, message)
    
    @state_handler("fill_missing_fields")
    def handle_fill_missing_fields(self, user_id: int, text: str):
        user_data = self.state_manager.get_data(user_id) or {}
        required_fields = ["first_name", "last_name", "vk_link", "age", "gender", "city"]

        # Заполняем первое пустое поле
        for field in required_fields:
            if not user_data.get(field):
                user_data[field] = text.strip()
                break

        self.state_manager.set_data(user_id, **user_data)

        # Проверка недостающих полей
        missing_fields = [rf for rf in required_fields if not user_data.get(rf)]
        if missing_fields:
            missing_fields_text = ", ".join(self.FIELD_NAMES_RU[f] for f in missing_fields)
            self.send_msg(user_id, f"Пожалуйста, укажите {missing_fields_text}:")
            return
      
        # Сохраняем пользователя в БД
        save_user_from_vk(
            vk_user_id=int(user_data["vk_id"]),
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            vk_link=user_data["vk_link"],
            age=int(user_data["age"]),
            gender=user_data["gender"],
            city=user_data["city"]
        )
        self.show_user_profile(user_id)
        self.state_manager.clear_state(user_id)
        self.send_msg(user_id, "Данные профиля сохранены", keyboard=self.keyboard)
        logger.info(f"Пользователь {user_id} сохранён: {user_data}")
        
    def handle_message(self, user_id: int, text: str):
        logger.info(f"Новое сообщение от {user_id}: {text}")    
        text_lower = text.lower()

        if text_lower in ["/start", "старт", "начать"]:
            # Если пользователь уже есть в базе
            user_in_db = get_user_by_vk_id(user_id)
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

            self.state_manager.set_data(user_id, **vk_info)
            self.show_user_profile(user_id)
            
            # Проверка недостающих полей
            user_data = {**vk_info, **(self.state_manager.get_data(user_id) or {})}
            required_fields = ["first_name", "last_name", "vk_link", "age", "gender", "city"]
            missing_fields = [f for f in required_fields if not user_data.get(f)]
            if missing_fields:
                self.state_manager.set_data(user_id, **user_data)
                self.state_manager.set_state(user_id, "fill_missing_fields")
                missing_fields_text = ", ".join(self.FIELD_NAMES_RU[f] for f in missing_fields)
                self.send_msg(user_id, f"Пожалуйста, укажите {missing_fields_text}:")
            else:
                save_user_from_vk(
                    vk_user_id=int(user_data["vk_id"]),
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    vk_link=user_data["vk_link"],
                    age=int(user_data["age"]),
                    gender=user_data["gender"],
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

        if text_lower == "поиск":
            ...

        if text_lower == "избранное":
            ...

        if text_lower == "помощь":
            self.send_msg(user_id, "Доступные команды:\nПоиск\nИзбранное\nНастройки", keyboard=self.keyboard)
            return

        self.send_msg(user_id, "Не понял команду. Напишите /start, чтобы начать.", keyboard=self.keyboard)

    def run(self) -> None:
        logger.info("Бот запущен")
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                request = event.text
                user_id = event.user_id
                if user_id and request:
                    self.handle_message(user_id, request)