import logging
import sys
from src.config import settings
from src.vk_bot.vk_bot import VkBot
from src.database.base import create_tables

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)-20s: %(message)s",
    handlers=[
        logging.FileHandler("vkinder.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def check_tokens() -> bool:
    # Проверка токенов
    tokens_ok = True
    messages = []

    if not settings.VK_GROUP_TOKEN or "your_group_token" in settings.VK_GROUP_TOKEN:
        messages.append("❌ Групповой токен не настроен!")
        tokens_ok = False

    if not settings.VK_USER_TOKEN or "your_user_token" in settings.VK_USER_TOKEN:
        messages.append("❌ Пользовательский токен не настроен!")
        tokens_ok = False

    if messages:
        for msg in messages:
            logger.error(msg)
        logger.info("\nКак получить токены:")
        logger.info("1. Групповой токен: Настройки группы → Работа с API → Ключи доступа")
        logger.info("2. Пользовательский токен: https://vk.com/dev/implicit_flow_user")

    return tokens_ok


def setup_database() -> bool:
    # Создание таблиц
    try:
        create_tables()
        logger.info("Таблицы базы данных созданы")
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        return False


def main():
    # Основная функция запуска
    logger.info("Запуск VKinder")

    # Проверка токенов
    if not check_tokens():
        sys.exit(1)

    # Настройка базы данных
    if not setup_database():
        sys.exit(1)

    # Запуск бота
    try:
        bot = VkBot(settings.VK_GROUP_TOKEN, settings.VK_USER_TOKEN)
        logger.info("Бот инициализирован, запуск...")
        bot.run()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
