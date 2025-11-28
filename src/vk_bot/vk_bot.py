from vk_api import VkApi
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from src.database.statemanager import StateManager


def state_handler(state_name):
    def decorator(func):
        func.state_name = state_name
        return func
    return decorator

class VkBot:
    
    def __init__(self, token) -> None:
        self.__token = token
        self.vk_session = VkApi(token=self.__token)
        self.longpoll = VkLongPoll(self.vk_session)
        self.vk = self.vk_session.get_api()    
        self.state_manager = StateManager()

    def send_msg(self, user_id: int, message: str):
        self.vk.messages.send(
            user_id=user_id,
            message=message,
            random_id=get_random_id()
        )

    def handle_message(self, user_id: int, text: str):
        current_state = self.state_manager.get_state(user_id)
        # Запускаем состояние, если есть
        if current_state:
            for attr in dir(self):
                handler = getattr(self, attr)
                if hasattr(handler, 'state_name') and handler.state_name == current_state:
                    handler(user_id, text)
        
        if text.lower() in ['начать', 'старт']:
            self.send_msg(user_id, 'Здравствуйте! Начинаем.')
            # Показываем клавиатуру
        elif text.lower() in ['помощь', 'help']:
            ...
            # Показать информацию
            # Показываем клавиатуру
        else:
            self.send_msg(user_id, "Напиши 'начать или старт'")
    
    def run(self) -> None:
        print("Бот запущен")
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                request = event.text
                user_id = event.user_id
                if user_id and request:
                    self.handle_message(user_id, request)