import logging
from typing import Dict, List, Optional, Tuple
from src.vk_bot.keyboards import get_main_keyboard, get_favorites_keyboard, get_blacklist_keyboard
from src.database.crud import (
    get_favorites,
    get_blacklist,
    remove_from_favorites,
    remove_from_blacklist,
    get_user_by_vk_id,
    add_interaction,
    is_interaction_exists
)

logger = logging.getLogger(__name__)


class InteractionHandlers:
    def __init__(self):
        self.active_modes: Dict[int, Dict] = {}
        logger.info("Инициализирован InteractionHandlers")
        
    def handle_favorites_command(self, vk_id: int) -> Tuple[str, str]:
        """Обработка команды 'Избранное'"""
        user = get_user_by_vk_id(vk_id)
        if not user:
            return "Сначала зарегистрируйтесь", get_main_keyboard()
        
        favorites = get_favorites(user.id)
        
        if not favorites:
            return "Избранное пусто", get_main_keyboard()
        
        # Формируем сообщение для первой страницы
        message = self._format_favorites_list(favorites, page=0)
        
        # Сохраняем состояние
        self.active_modes[vk_id] = {
            'mode': 'favorites',
            'bot_user_id': user.id,
            'items': favorites,
            'page': 0  # Текущая страница
        }
        
        items_per_page = 5
        total_pages = (len(favorites) + items_per_page - 1) // items_per_page
        show_main_menu = total_pages > 1
        
        return message, get_favorites_keyboard(show_main_menu=show_main_menu)
    
    def _format_favorites_list(self, favorites: List, page: int = 0) -> str:
        """Форматирует список избранного"""
        items_per_page = 5
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        
        current_items = favorites[start_idx:end_idx]
        
        message = f"**Избранное** (стр. {page + 1}):\n\n"
        
        for i, fav in enumerate(current_items, start=1):
            num = start_idx + i
            message += f"{num}. {fav.vk_name or 'Без имени'}\n"
            if fav.profile_link:
                message += f"{fav.profile_link}\n"
            message += "\n"
        
        total_pages = (len(favorites) + items_per_page - 1) // items_per_page
        if total_pages > 1:
            message += f"Страница {page + 1} из {total_pages}\n"
            message += "Используйте 'далее' или 'назад' для навигации\n"
        
        message += "\n**Команды:**\n"
        message += "• `удалить 1` - удалить первую запись\n"
        message += "• `назад` / `далее` - листать страницы\n"
        message += "• `очистить все` - удалить всё\n"
        return message
        
    def handle_blacklist_command(self, user_id: int) -> Tuple[str, str]:
        """Обработка команды 'Черный список' - показывает список"""
        user = get_user_by_vk_id(user_id)
        if not user:
            return "Сначала зарегистрируйтесь", get_main_keyboard()
        
        blacklist = get_blacklist(user.id)
        
        if not blacklist:
            return "Черный список пуст", get_main_keyboard()
        
        # Формируем сообщение
        message = self._format_blacklist_list(blacklist)
        
        # Сохраняем режим
        self.active_modes[user_id] = {
            'mode': 'blacklist',
            'bot_user_id': user.id,
            'items': blacklist,
            'page': 0
        }
        
        items_per_page = 5
        total_pages = (len(blacklist) + items_per_page - 1) // items_per_page
        show_main_menu = total_pages > 1
        
        return message, get_blacklist_keyboard(show_main_menu=show_main_menu)
    
    def _format_blacklist_list(self, blacklist: List, page: int = 0) -> str:
        """Форматирует список черного списка"""
        items_per_page = 5
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        
        current_items = blacklist[start_idx:end_idx]
        
        message = f"**Черный список** (стр. {page + 1}):\n\n"
        
        for i, blocked in enumerate(current_items, start=1):
            num = start_idx + i
            message += f"{num}. {blocked.vk_name or 'Без имени'}\n"
            if blocked.profile_link:
                message += f"   🔗 {blocked.profile_link}\n"
            message += "\n"
        
        total_pages = (len(blacklist) + items_per_page - 1) // items_per_page
        if total_pages > 1:
            message += f"Страница {page + 1} из {total_pages}\n"
            message += "Используйте 'далее' или 'назад' для навигации\n"
        
        message += "\nЧтобы разблокировать: разблокировать [номер]"
        return message
        
    def handle_interaction_command(self, user_id: int, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Обрабатывает команды в режиме избранного/черного списка"""
        if user_id not in self.active_modes:
            return None, None
        
        mode_data = self.active_modes[user_id]
        mode = mode_data['mode']
        text_lower = text.lower().strip()
        
        items_per_page = 5
        total_pages = (len(mode_data['items']) + items_per_page - 1) // items_per_page
        current_page = mode_data['page']
        show_main_menu = total_pages > 1        
        
        keyboard = get_favorites_keyboard() if mode == 'favorites' else get_blacklist_keyboard(show_main_menu=show_main_menu)
        
        # Навигация
        if text_lower == 'назад':
            if current_page == 0:
                del self.active_modes[user_id]
                return "Возвращаюсь в главное меню", get_main_keyboard()
            else:
                mode_data['page'] -= 1
                
                total_pages = (len(mode_data['items']) + items_per_page - 1) // items_per_page
                show_main_menu = total_pages > 1
                keyboard = get_favorites_keyboard(show_main_menu=show_main_menu) if mode == 'favorites' else get_blacklist_keyboard(show_main_menu=show_main_menu)
                
                if mode == 'favorites':
                    return self._format_favorites_list(mode_data['items'], mode_data['page']), keyboard
                else:
                    return self._format_blacklist_list(mode_data['items'], mode_data['page']), keyboard
            
        elif text_lower == 'далее':
            
            if current_page < total_pages - 1:
                mode_data['page'] += 1
                new_page = mode_data['page']
                show_main_menu = total_pages > 1
                keyboard = get_favorites_keyboard(show_main_menu=show_main_menu) if mode == 'favorites' else get_blacklist_keyboard(show_main_menu=show_main_menu)
                
                if mode == 'favorites':
                    return self._format_favorites_list(mode_data['items'], new_page), keyboard
                else:
                    return self._format_blacklist_list(mode_data['items'], new_page), keyboard
            else:
                return "Это последняя страница", keyboard
        
        elif text_lower == 'главное меню':
            del self.active_modes[user_id]
            return "Возвращаюсь в главное меню", get_main_keyboard()
        elif text_lower == 'очистить все':
            if mode == 'favorites':
                for item in mode_data['items']:
                    remove_from_favorites(mode_data['bot_user_id'], item.vk_id)
                del self.active_modes[user_id]
                return "Все удалено из избранного", get_main_keyboard()
            else:
                for item in mode_data['items']:
                    remove_from_blacklist(mode_data['bot_user_id'], item.vk_id)
                del self.active_modes[user_id]
                return "Черный список очищен", get_main_keyboard()
        
        # Удаление/разблокировка по номеру
        elif text_lower.startswith('удалить') and mode == 'favorites':
            return self._handle_remove_favorite(user_id, text, mode_data)
        
        elif text_lower.startswith('разблокировать') and mode == 'blacklist':
            return self._handle_unblock_user(user_id, text, mode_data)
        
        return "Используйте кнопки или команды", keyboard
    
    def _handle_remove_favorite(self, user_id: int, text: str, mode_data: Dict) -> Tuple[str, str]:
        """Удаляет из избранного по номеру"""
        try:
            parts = text.split()
            if len(parts) != 2:
                return "Используйте: удалить [номер]", get_favorites_keyboard()
            
            num = int(parts[1]) - 1
            if 0 <= num < len(mode_data['items']):
                item = mode_data['items'][num]
                if remove_from_favorites(mode_data['bot_user_id'], item.vk_id):
                    mode_data['items'] = get_favorites(mode_data['bot_user_id'])
                    
                    if not mode_data['items']:
                        del self.active_modes[user_id]
                        return "✅ Удалено. Избранное пусто", get_main_keyboard()
                    
                    return self._format_favorites_list(mode_data['items'], mode_data['page']), get_favorites_keyboard()
                else:
                    return "Ошибка удаления", get_favorites_keyboard()
            else:
                return "Неверный номер", get_favorites_keyboard()
        except (ValueError, IndexError):
            return "Используйте: удалить [номер]", get_favorites_keyboard()
    
    def _handle_unblock_user(self, user_id: int, text: str, mode_data: Dict) -> Tuple[str, str]:
        """Разблокирует пользователя по номеру"""
        try:
            parts = text.split()
            if len(parts) != 2:
                return "Используйте: разблокировать [номер]", get_blacklist_keyboard()
            
            num = int(parts[1]) - 1
            if 0 <= num < len(mode_data['items']):
                item = mode_data['items'][num]
                if remove_from_blacklist(mode_data['bot_user_id'], item.vk_id):
                    # Обновляем список
                    mode_data['items'] = get_blacklist(mode_data['bot_user_id'])
                    
                    if not mode_data['items']:
                        del self.active_modes[user_id]
                        return "Разблокировано. Черный список пуст", get_main_keyboard()
                    
                    return self._format_blacklist_list(mode_data['items'], mode_data['page']), get_blacklist_keyboard()
                else:
                    return "Ошибка разблокировки", get_blacklist_keyboard()
            else:
                return "Неверный номер", get_blacklist_keyboard()
        except (ValueError, IndexError):
            return "Используйте: разблокировать [номер]", get_blacklist_keyboard()
    
    def is_in_interaction_mode(self, user_id: int) -> bool:
        """Проверяет, находится ли пользователь в режиме избранного/черного списка"""
        return user_id in self.active_modes