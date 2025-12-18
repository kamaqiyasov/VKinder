from typing import Optional
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

def get_start_keyboard():
    """Клавиатура для новых пользователей"""
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Старт', color=VkKeyboardColor.POSITIVE)

    return keyboard.get_keyboard()

def get_main_keyboard():
    """Основная клавиатура для зарегистрированных пользователей"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('Поиск', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Избранные', color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button('Черный список', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button('Настройки', color=VkKeyboardColor.SECONDARY)
    
    return keyboard.get_keyboard()

def get_search_keyboard():
    """Клавиатура для режима поиска"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('В избранное', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('Дальше', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('В черный список', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('Главное меню', color=VkKeyboardColor.PRIMARY)
    
    return keyboard.get_keyboard()

def get_settings_keyboard():
    """Клавиатура для настроек поиска"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('Изменить возраст', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Изменить город', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('С фото', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('Главное меню', color=VkKeyboardColor.SECONDARY)
    
    return keyboard.get_keyboard()

def get_favorites_keyboard(show_main_menu: bool = False):
    """Клавиатура для избранного"""
    keyboard = VkKeyboard(one_time=False)
    
    if show_main_menu:
        keyboard.add_button('Главное меню', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
    
    keyboard.add_button('Назад', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('Далее', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Очистить все', color=VkKeyboardColor.NEGATIVE)
    
    return keyboard.get_keyboard()

def get_blacklist_keyboard(show_main_menu: bool = False):
    """Клавиатура для черного списка"""
    keyboard = VkKeyboard(one_time=False)
    
    if show_main_menu:
        keyboard.add_button('Главное меню', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
    
    keyboard.add_button('Назад', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('Далее', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Очистить все', color=VkKeyboardColor.NEGATIVE)
    
    return keyboard.get_keyboard()

def get_auth_keyboard(auth_url: Optional[str] = None):
    keyboard = VkKeyboard(one_time=False, inline=True)
    if auth_url:
        keyboard.add_openlink_button("Авторизоваться в VK", link=auth_url)
        keyboard.add_line()
    keyboard.add_button("Проверить авторизацию", color=VkKeyboardColor.POSITIVE)
    
    return keyboard.get_keyboard()