from vk_api.keyboard import VkKeyboard, VkKeyboardColor


class VkBotKeyboards:
    @staticmethod
    def create_main_keyboard():
        # Основная клавиатура для существующих пользователей
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button('Поиск', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Избранное', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Настройки', color=VkKeyboardColor.SECONDARY)
        keyboard.add_button('Помощь', color=VkKeyboardColor.SECONDARY)
        return keyboard

    @staticmethod
    def create_welcome_keyboard():
        # Приветственная клавиатура для новых пользователей
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button('Старт', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Помощь', color=VkKeyboardColor.SECONDARY)
        return keyboard

    @staticmethod
    def create_search_keyboard():
        # Клавиатура поиска
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button('Начать поиск', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Мои настройки', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Назад', color=VkKeyboardColor.NEGATIVE)
        return keyboard

    @staticmethod
    def create_viewing_keyboard():
        # Клавиатура просмотра анкет
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button('❤️ В избранное', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('👍 Лайк фото', color=VkKeyboardColor.POSITIVE)
        keyboard.add_line()
        keyboard.add_button('➡️ Далее', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('👎 В черный список', color=VkKeyboardColor.NEGATIVE)
        keyboard.add_line()
        keyboard.add_button('💾 Мои лайки', color=VkKeyboardColor.SECONDARY)
        keyboard.add_button('🏠 В меню', color=VkKeyboardColor.SECONDARY)
        return keyboard

    @staticmethod
    def create_settings_keyboard():
        # Клавиатура настроек
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button("Изменить возраст", color=VkKeyboardColor.PRIMARY)
        keyboard.add_button("Изменить город", color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button("Изменить пол", color=VkKeyboardColor.PRIMARY)
        keyboard.add_button("Очистить историю", color=VkKeyboardColor.NEGATIVE)
        keyboard.add_line()
        keyboard.add_button("Назад", color=VkKeyboardColor.SECONDARY)
        return keyboard

    @staticmethod
    def create_photo_choice_keyboard():
        # Клавиатура выбора фотографии
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('1', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('2', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('3', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('Отмена', color=VkKeyboardColor.NEGATIVE)
        return keyboard

    @staticmethod
    def create_photo_selection_keyboard(photo_count: int):
        # Клавиатура выбора фотографии
        keyboard = VkKeyboard(one_time=True)
        for i in range(1, min(photo_count, 5) + 1):  # максимум 5 кнопок
            keyboard.add_button(str(i), color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('Отмена', color=VkKeyboardColor.NEGATIVE)
        return keyboard

