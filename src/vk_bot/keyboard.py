# src/vk_bot/keyboard.py
from vk_api.keyboard import VkKeyboard, VkKeyboardColor


class KeyboardManager:
    @staticmethod
    def create_start_keyboard():
        """Создание стартовой клавиатуры с кнопкой Начать"""
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('Начать', color=VkKeyboardColor.PRIMARY)
        return keyboard

    @staticmethod
    def create_main_keyboard():
        """Создание основной клавиатуры"""
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button('Профиль', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Избранные', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Чёрный список', color=VkKeyboardColor.SECONDARY)
        keyboard.add_button('Смотреть анкеты', color=VkKeyboardColor.POSITIVE)
        return keyboard

    @staticmethod
    def create_dating_keyboard():
        """Создание клавиатуры для режима просмотра анкет"""
        keyboard = VkKeyboard(one_time=False)

        # Первая строка
        keyboard.add_button('Нравится', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Не нравится', color=VkKeyboardColor.NEGATIVE)

        # Вторая строка
        keyboard.add_line()
        keyboard.add_button('Добавить в избранное', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Добавить в ЧС', color=VkKeyboardColor.SECONDARY)

        # Третья строка
        keyboard.add_line()
        keyboard.add_button('В главное меню', color=VkKeyboardColor.PRIMARY)

        return keyboard

    @staticmethod
    def get_keyboard_by_state(state: str):
        """Получение клавиатуры по состоянию"""
        keyboards = {
            'start': KeyboardManager.create_start_keyboard,
            'awaiting_start': KeyboardManager.create_start_keyboard,
            'main': KeyboardManager.create_main_keyboard,
            'dating': KeyboardManager.create_dating_keyboard
        }

        if state in keyboards:
            return keyboards[state]()
        return None  # Для состояний без клавиатуры (например, registration)