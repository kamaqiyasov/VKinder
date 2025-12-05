from vk_api.keyboard import VkKeyboard, VkKeyboardColor

class VkBotKeyboards:
    @staticmethod
    def create_main_keyboard():
        # Основная клавиатура
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button('Поиск', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Избранное', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Настройки', color=VkKeyboardColor.SECONDARY)
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
        keyboard.add_button('➡️ Далее', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('👎 В черный список', color=VkKeyboardColor.NEGATIVE)
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
        keyboard.add_button("Назад", color=VkKeyboardColor.NEGATIVE)
        return keyboard

    @staticmethod
    def create_viewing_keyboard_with_likes():
        # Клавиатура просмотра анкет с лайками фото
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button('❤️ В избранное', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('👍 Лайк фото', color=VkKeyboardColor.POSITIVE)
        keyboard.add_line()
        keyboard.add_button('➡️ Далее', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('👎 В ЧС', color=VkKeyboardColor.NEGATIVE)
        keyboard.add_line()
        keyboard.add_button('💾 Мои лайки', color=VkKeyboardColor.SECONDARY)
        keyboard.add_button('🏠 В меню', color=VkKeyboardColor.SECONDARY)
        return keyboard