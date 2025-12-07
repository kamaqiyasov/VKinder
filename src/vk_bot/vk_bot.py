import logging
from typing import Optional
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
from src.database.crud import get_blacklist, get_favorites, get_or_create_search_settings, get_user_by_vk_id
from src.database.models import BotUser
from src.vk_bot.handlers.search_handlers import SearchHandlers
from src.vk_bot.keyboards import get_blacklist_keyboard, get_favorites_keyboard, get_main_keyboard, get_search_keyboard, get_start_keyboard
from src.vk_bot.handlers.settings_handlers import SettingsHandlers
from src.vk_bot.handlers.interaction_handlers import InteractionHandlers
from src.vk_bot.handlers.user_handlers import UserHandlers
from src.vk_bot.vk_client import VKClient

logger = logging.getLogger(__name__)

class VkBot:
    def __init__(self, group_token: str, group_id: int) -> None:
        logger.info(f"Инициализация бота, группа ID: {group_id}")
        self.vk_session = vk_api.VkApi(token=group_token)
        self.api = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, group_id)
        self.vk_client = VKClient()
        self.user_handlers = UserHandlers()
        self.settings_handlers = SettingsHandlers()
        self.search_handlers = SearchHandlers(self.vk_client, send_message_callback=self._send_msg)
        self.interaction_handlers = InteractionHandlers()
            
        self.commands = {
            "старт": self._handle_start,
            "токен": self._handle_token,
            "поиск": self._handle_search,
            "избранные": self._handle_favorites,
            "черный список": self._handle_blacklist,
            "настройки": self._handle_settings,
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
        
        # Проверяем состояние добавления пользователя
        if self.user_handlers.has_active_state(user_id):
            _, response = self.user_handlers.handle_state_response(user_id, text)
            if response:
                self._send_msg(user_id, response, get_main_keyboard())
            return
        
        if text.startswith("token="):
            token = text[6:].strip()
            _, response = self.user_handlers.handle_token_input(self.vk_client, user_id, token)
            if response:
                self._send_msg(user_id, response)
            return
        
        text_lower = text.lower().strip()
        handler = self.commands.get(text_lower, self._handle_unknown)
        handler(user_id)
        
    def _handle_start(self, user_id: int):
        is_registered, user = self._is_user_registered(user_id)
        if is_registered and user:
            self._send_msg(user_id, "Привет! Выбери действие:", get_main_keyboard())
        elif user:
            self._send_msg(user_id, "Токен устарел: пропиши 'токен' для инструкции")
        else:
            self._send_msg(user_id, "Нужен токен: пропиши 'токен' для инструкции")
        
    def _handle_unknown(self, user_id: int):
        user = get_user_by_vk_id(user_id)
        if user and user.access_token:
            self._send_msg(user_id, "Выбери действие на клавиатуре", get_main_keyboard())
        else:
            self._send_msg(user_id, "Напиши 'Старт' чтобы начать", get_start_keyboard())

    def _handle_token(self, user_id: int):
        user = get_user_by_vk_id(user_id)        
        if user and user.access_token:
            self._send_msg(user_id, "У тебя уже есть токен. Используй клавиатуру", get_main_keyboard())
            return       
        instruction = self.user_handlers.get_token_instruction()
        self._send_msg(user_id, instruction)
    
    def _is_user_registered(self, user_id: int) -> tuple[bool, Optional[BotUser]]:
        """Проверяет, зарегистрирован ли пользователь"""
        user = get_user_by_vk_id(user_id)
        if not user or not user.access_token:
            return False, None
        
        if not self.vk_client.is_authenticated():
            self.vk_client.set_token(user.access_token)
        
        token_valid = self.vk_client.is_authenticated()
        return token_valid, user if token_valid else None
    
    def _require_registration(self, user_id: int) -> Optional[BotUser]:
        """Проверяет регистрацию, отправляет сообщение если нет"""
        is_registered, user = self._is_user_registered(user_id)
        
        if not is_registered:
            if user:  # Пользователь есть, но токен невалидный
                self._send_msg(user_id, "Токен устарел: пропиши 'токен' для инструкции")
            else:  # Пользователя нет
                self._send_msg(user_id, "Сначала зарегистрируйся: 'Старт'")
            return None
        
        return user
    
    def _handle_search(self, user_id: int):
        """Обработка кнопки Поиск"""
        user = self._require_registration(user_id)
        if not user:
            return
        
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