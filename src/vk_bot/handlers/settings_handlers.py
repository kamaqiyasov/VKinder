import logging
from typing import Dict, Optional, Tuple
from src.database.crud import get_or_create_search_settings, update_search_settings
from src.vk_bot.keyboards import get_main_keyboard, get_settings_keyboard

logger = logging.getLogger(__name__)

class SettingsHandlers:
    def __init__(self):
        self.user_states: Dict[int, Dict] = {}
        logger.info("Инициализирован SettingsService")
    
    def handle_settings_command(self, bot_user_id: int, vk_user_id: int) -> Tuple[str, str]:
        """Обработка команды 'Настройки'"""
        logger.info(f"Пользователь {vk_user_id}: запрос настроек")
        settings = get_or_create_search_settings(bot_user_id)
        if settings is None:
            error_msg = "Ошибка: настройки не найдены"
            return error_msg, get_main_keyboard()
            
        message = (
            "**Настройки поиска:**\n\n"
            f"Возраст: {settings.age_from} - {settings.age_to} лет\n"
            f"Город: {settings.city or 'не указан'}\n"
            f"Только с фото: {'Да' if settings.has_photo else 'Нет'}\n\n"
            "Выбери что изменить:"
        )
        self.user_states[vk_user_id] = {
            'bot_user_id': bot_user_id,
            'mode': 'settings_menu'
        }
        
        return message, get_settings_keyboard()
    
    def handle_settings_response(self, vk_user_id: int, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Обработка ответа в режиме настроек"""
        if vk_user_id not in self.user_states:
            return None, None
        
        state = self.user_states[vk_user_id]
        text_lower = text.lower().strip()
        
        if text_lower == "изменить возраст":
            state['awaiting'] = 'age'
            return "Введи диапазон возраста (например: 25-30)", None
            
        elif text_lower == "изменить город":
            state['awaiting'] = 'city'
            return "Введи новый город для поиска:", None
            
        elif text_lower == "с фото":
            settings = get_or_create_search_settings(state['bot_user_id'])
            if settings is None:
                return "Ошибка: настройки не найдены", get_settings_keyboard()
            new_value = not settings.has_photo
            update_search_settings(state['bot_user_id'], has_photo=new_value)
            
            status = "включены" if new_value else "выключены"
            return f"Поиск только с фото: {status}", get_settings_keyboard()
            
        elif text_lower == "главное меню":
            del self.user_states[vk_user_id]
            return "Возвращаюсь в главное меню", get_main_keyboard()
            
        elif 'awaiting' in state:
            if state['awaiting'] == 'age':
                return self._process_age_input(vk_user_id, state, text)
            elif state['awaiting'] == 'city':
                return self._process_city_input(vk_user_id, state, text)
        
        return None, None
    
    def _process_age_input(self, vk_user_id: int, state: Dict, text: str) -> Tuple[str, str]:
        """Обработка ввода возраста"""
        try:
            if '-' in text:
                age_from, age_to = map(int, text.split('-'))
            else:
                age = int(text)
                age_from = max(18, age - 3)
                age_to = min(100, age + 3)
            
            if 18 <= age_from <= age_to <= 100:
                update_search_settings(state['bot_user_id'], age_from=age_from, age_to=age_to)
                message = f"Диапазон возраста установлен: {age_from}-{age_to} лет"
                del state['awaiting']
            else:
                message = "Возраст должен быть от 18 до 100 лет"
            
            return message, get_settings_keyboard()
        except:
            return "Неверный формат. Пример: 25-30 или 27", get_settings_keyboard()
    
    def _process_city_input(self, vk_user_id: int, state: Dict, text: str) -> Tuple[str, str]:
        """Обработка ввода города"""
        if len(text.strip()) < 2:
            return "Название города слишком короткое", get_settings_keyboard()
        
        update_search_settings(state['bot_user_id'], city=text.strip())
        del state['awaiting']
        
        return f"Город поиска: {text.strip()}", get_settings_keyboard()
    
    def has_active_settings_state(self, vk_user_id: int) -> bool:
        """Проверяет активное состояние настроек"""
        return vk_user_id in self.user_states