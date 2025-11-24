from random import randrange

from vk_api import VkApi
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

from src.vk_bot.queries import create_user, user_exists
from src.vk_bot.vk_client import VKUser


class VkBot:
    
    def __init__(self, token) -> None:
        self.__token = token
        self.vk_session = VkApi(token=self.__token)
        self.longpoll = VkLongPoll(self.vk_session)
        self.vk = self.vk_session.get_api()
        
    def send_msg(self, user_id: int, message: str):
        self.vk.messages.send(
            user_id=user_id,
            message=message,
            random_id=get_random_id()
        )
        
    def handle_message(self, user_id: int, text: str):
        pass
        # if not user_exists(user_id):
        #     self.send_msg(user_id, "Добро пожаловать!")
        #     # create_user(user_id, user_info['first_name'], "last_name", f"https://vk.com/id{user_info['id']}", 25, "Мужской", "Москва")
        # else:
        #     self.send_msg(user_id, "Добро пожаловать! Нам нужно собрать некоторую информацию о вас.")
        #     self.start_info_collection(user_id)
        
    def run(self):
        print("Бот запущен")
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                request = event.text
                user_id = event.user_id
                if user_id and request:
                    self.handle_message(user_id, request)