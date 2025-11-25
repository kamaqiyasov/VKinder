from vk_api import VkApi
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

from src.vk_bot.vk_queries import create_user, user_exists
from src.vk_bot.vk_state_maneger import StateManager, state_handler

class VkBot:
    
    def __init__(self, token) -> None:
        self.__token = token
        self.vk_session = VkApi(token=self.__token)
        self.longpoll = VkLongPoll(self.vk_session)
        self.vk = self.vk_session.get_api()
    
        self.user_states = {}
        self.state_manager = StateManager(self)

    def send_msg(self, user_id: int, message: str):
        self.vk.messages.send(
            user_id=user_id,
            message=message,
            random_id=get_random_id()
        )
    @state_handler("start")
    def handle_start(self, user_id: int, text: str) -> None:
        if text in ["начать", "привет"]:
            if user_exists(user_id):
                self.send_msg(user_id, "С возвращением! Вы уже зарегистрированы.")
                self.user_states[user_id] = "main"
            else:
                self.send_msg(user_id, "Привет! Давай зарегистрируем тебя в системе.")
                self.user_states[user_id] = "registration"
        else:
            self.send_msg(user_id, "Напишите 'Начать' или 'Привет' для начала работы")
    
    @state_handler("main")
    def handle_main(self, user_id: int, text: str):
        self.send_msg(user_id, "Вы в главном меню")
    
    @state_handler("registration") 
    def handle_registration(self, user_id: int, text: str):
        self.send_msg(user_id, "Регистрация...")
        
    def handle_message(self, user_id: int, text: str) -> None:
        text = text.lower()
        self.state_manager.handle_state(user_id, text)
    
    def run(self) -> None:
        print("Бот запущен")
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                request = event.text
                user_id = event.user_id
                if user_id and request:
                    self.handle_message(user_id, request)