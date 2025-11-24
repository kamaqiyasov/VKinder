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
        
        if not user_exists(user_id):
            create_user(user_id, "Иван", "Иванов", "https://vk.com/id123", 25, "Мужской", "Москва")                
        
        
        
        # vk_user = VKUser(self.__token, user_id)
        # user_info = vk_user.user_info()
        
        # if user_info['is_closed']:
        #     self.send_msg(user_id, f"К сожалению, у вас закрытый аккаунт. Можете указать данные вручную")
            
        # text = text.lower().strip()
        # if text.startswith('/'):
        #     self.send_msg(user_id, "Привет")
        # else:
        #     self.send_msg(user_id, f"К сожалению, у вас закрытый аккаунт. Можете указать данные вручную")
            
    def run(self):
        print("Бот запущен")
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                request = event.text
                user_id = event.user_id
                if user_id and request:
                    self.handle_message(user_id, request)