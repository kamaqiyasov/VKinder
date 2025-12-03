import logging

from vk_api import VkApi
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from src.database.crud import get_user_by_vk_id, save_user_from_vk
from src.database.statemanager import StateManager
from src.vk_bot.vk_client import VKUser
from src.vk_bot.handlers import Handlers
from src.vk_bot.keyboard import KeyboardManager


logger = logging.getLogger(__name__)


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
        self.state_manager = StateManager()
        self.handlers = Handlers(self)
        self.keyboard_manager = KeyboardManager()

    def send_msg(self, user_id: int, message: str, keyboard=None, state: str = None):
        params = {
            "user_id": user_id,
            "message": message,
            "random_id": get_random_id()
        }
        
        # Если указано состояние - берем клавиатуру по состоянию
        if state and not keyboard:
            keyboard = self.keyboard_manager.get_keyboard_by_state(state)
        
        # Если есть клавиатура (любая) - добавляем в параметры
        if keyboard:
            params["keyboard"] = keyboard.get_keyboard()

        self.vk.messages.send(**params)
        logger.info(f"Отправлено сообщение пользователю {user_id}: {message}")
    
    def run(self) -> None:
        logger.info("Бот запущен")
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                request = event.text
                user_id = event.user_id
                if user_id and request:
                    self.handle_message(user_id, request)
    
    def handle_message(self, user_id: int, request: str):
        """Обработка входящего сообщения"""
        # Получаем текущее состояние пользователя
        current_state = self.state_manager.get_state(user_id)
        
        # Если у пользователя нет состояния - это первый запуск
        if current_state is None:
            current_state = "awaiting_start"  # Состояние ожидания команды "Начать"
            self.state_manager.set_state(user_id, "awaiting_start")
        
        # Ищем обработчик для этого состояния
        handler_name = f"handle_{current_state}"
        handler = getattr(self.handlers, handler_name, None)
        
        if handler:
            handler(user_id, request)
        else:
            # Обработчик по умолчанию - ожидание старта
            logger.warning(f"Нет обработчика для состояния {current_state}, сбрасываем в awaiting_start")
            self.state_manager.set_state(user_id, "awaiting_start")
            self.handlers.handle_start(user_id, request)