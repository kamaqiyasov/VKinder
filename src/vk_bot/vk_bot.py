from vk_api import VkApi
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

from src.database.statemanager import StateManager
from src.vk_bot.vk_queries import create_user, user_exists

class VkBot:
    
    def __init__(self, token) -> None:
        self.__token = token
        self.vk_session = VkApi(token=self.__token)
        self.longpoll = VkLongPoll(self.vk_session)
        self.vk = self.vk_session.get_api()
    
        self.state_manager = StateManager()
        self.STATES = {
            'MENU': 'menu',
            'AWAITING_NAME': 'awaiting_city', 
            'AWAITING_AGE': 'awaiting_age'
        }

    def send_msg(self, user_id: int, message: str):
        self.vk.messages.send(
            user_id=user_id,
            message=message,
            random_id=get_random_id()
        )

    def handle_message(self, user_id: int, text: str) -> None:
        pass
    
    def run(self) -> None:
        print("Бот запущен")
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                request = event.text
                user_id = event.user_id
                if user_id and request:
                    self.handle_message(user_id, request)