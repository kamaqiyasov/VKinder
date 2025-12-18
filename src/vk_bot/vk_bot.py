import logging
from typing import Optional
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
from src.database.crud import get_user_by_vk_id
from src.database.models import BotUser
from src.vk_bot.handlers.search_handlers import SearchHandlers
from src.vk_bot.keyboards import get_auth_keyboard, get_main_keyboard, get_start_keyboard
from src.vk_bot.handlers.settings_handlers import SettingsHandlers
from src.vk_bot.handlers.interaction_handlers import InteractionHandlers
from src.vk_bot.handlers.user_handlers import UserHandlers
from src.vk_bot.vk_client import VKClient

logger = logging.getLogger(__name__)

class VkBot:
    def __init__(self, group_token: Optional[str], group_id: Optional[int]) -> None:
        logger.info(f"Инициализация бота, группа ID: {group_id}")
        self.vk_session = vk_api.VkApi(token=group_token)
        self.api = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, group_id)
        self.vk_client = None
        self.search_handlers = None
        self.user_handlers = UserHandlers()
        self.settings_handlers = SettingsHandlers()
        self.interaction_handlers = InteractionHandlers()
        
        self.commands = {
            "старт": self._handle_start,
            "поиск": self._handle_search,
            "избранные": self._handle_favorites,
            "черный список": self._handle_blacklist,
            "настройки": self._handle_settings,
            "проверить авторизацию": self._handle_check_token
        }
        logger.info("Бот инициализирован")
    
    def _send_msg(self, user_id: int, message: str, keyboard=None, attachment=None) -> None:
        self.api.messages.send(user_id=user_id, message=message, keyboard=keyboard, attachment=attachment, random_id=get_random_id())
         
    def run(self) -> None:
        logger.info(f"Бот запущен")
        for event in self.longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                message = event.object.message
                if message:
                    user_id = message['from_id']
                    text = message['text']
                    logger.info(f"Сообщение от {user_id}: {text}")
                    self._route_message(user_id, text)
    
    def _route_message(self, user_id: int, text: str):
        
        # Проверяем режим избранного/черного списка
        if self.interaction_handlers.is_in_interaction_mode(user_id):
            message, keyboard = self.interaction_handlers.handle_interaction_command(user_id, text)
            if message:
                self._send_msg(user_id, message, keyboard)
            return
        
        # Проверяем режим поиска
        if self.search_handlers is not None:
            if self.search_handlers.is_in_search_mode(user_id):
                message, keyboard, candidate = self.search_handlers.handle_search_command(user_id, text)
                if message:
                    attachment = None
                    if candidate:
                        attachment = self.search_handlers.get_candidate_attachment(candidate)
                    self._send_msg(user_id, message, keyboard, attachment)
                return
        
        # Проверяем состояние настроек
        if self.settings_handlers.has_active_settings_state(user_id):
            message, keyboard = self.settings_handlers.handle_settings_response(user_id, text)
            if message:
                self._send_msg(user_id, message, keyboard)
            return
        
        # Проверяем активное состояние пользователя
        if self.user_handlers.has_active_state(user_id):
            _, response = self.user_handlers.handle_state_response(user_id, text)
            if response:
                self._send_msg(user_id, response, get_main_keyboard())
            return
        
        text_lower = text.lower().strip()
        handler = self.commands.get(text_lower, self._handle_unknown)
        handler(user_id)
        
    def _handle_start(self, user_id: int):
        # is_registered, user = self._is_user_registered(user_id)
        has_token = self.user_handlers.check_token_exists(user_id)
        if has_token:
            welcome_msg = self.user_handlers.get_welcome_back_message(user_id)
            self._send_msg(user_id, f"{welcome_msg}\n\nВыбери действие:", get_main_keyboard())
        else:
            message, auth_url = self.user_handlers.get_auth_instruction(user_id)
            self._send_msg(user_id, message, get_auth_keyboard(auth_url))        
    
    def _handle_check_token(self, user_id: int):
        """Проверка авторизации (через inline кнопку или команду)"""
        has_token = self.user_handlers.check_token_exists(user_id)
        if has_token:
            is_register, msg = self.user_handlers.handle_token_input(self.vk_client, user_id, has_token)
            if is_register and self.vk_client is not None:
                self._send_msg(user_id, "Авторизация успешна! Теперь доступны все функции.", get_main_keyboard())
            else:
                self._send_msg(user_id, f"Для завершения регистрации нужна дополнительная информация: \n {msg}")
        else:
            self._send_msg(user_id, "Токен не найден", get_auth_keyboard())

    def _handle_unknown(self, user_id: int):
        has_token = self.user_handlers.check_token_exists(user_id)
        if has_token:
            self._send_msg(user_id, "Выбери действие на клавиатуре", get_main_keyboard())
        else:
            self._send_msg(user_id, "Напиши 'Старт' чтобы начать.", get_start_keyboard())
    
    def _handle_search(self, user_id: int):
        """Обработка кнопки Поиск"""
        token = self.user_handlers.check_token_exists(user_id)
        if not token:
            return
        
        self.vk_client = VKClient(user_id, token)
        self.search_handlers = SearchHandlers(self.vk_client, self.api, send_message_callback=self._send_msg)
        
        # Запускаем поиск
        message, keyboard, candidate_data = self.search_handlers.start_search(user_id)        
        
        # Получаем attachment для фото
        attachment = None
        if candidate_data:
            attachment = self.search_handlers.get_candidate_attachment(candidate_data)
                
        self._send_msg(user_id, message, keyboard, attachment)
          
    def _handle_favorites(self, user_id: int):
        """Обработка кнопки Избранные"""
        user = self._require_registration(user_id)
        if not user:
            return
        
        message, keyboard = self.interaction_handlers.handle_favorites_command(user_id)
        self._send_msg(user_id, message, keyboard)

    def _handle_blacklist(self, user_id: int):
        """Обработка кнопки Черный список"""
        user = self._require_registration(user_id)
        if not user:
            return
        
        message, keyboard = self.interaction_handlers.handle_blacklist_command(user_id)
        self._send_msg(user_id, message, keyboard)
    
    def _handle_settings(self, user_id: int):
        """Обработка кнопки Настройки"""
        user = self._require_registration(user_id)
        if not user:
            return
        
        message, keyboard = self.settings_handlers.handle_settings_command(user.id, user_id)
        self._send_msg(user_id, message, keyboard)