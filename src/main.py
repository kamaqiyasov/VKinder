import logging
from src.config import settings
from src.vk_bot.vk_bot import VkBot
from src.database.base import create_tables

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("vkinder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Запуск программы")

    # ДОБАВЛЯЕМ ПРОВЕРКУ ТОКЕНОВ
    logger.info(f"Групповой токен: {'ЕСТЬ' if settings.VK_GROUP_TOKEN else 'ОТСУТСТВУЕТ'}")
    logger.info(f"Пользовательский токен: {'ЕСТЬ' if settings.VK_USER_TOKEN else 'ОТСУТСТВУЕТ'}")

    # Проверяем длину токенов (безопасный вывод)
    if settings.VK_GROUP_TOKEN:
        logger.info(f"Длина группового токена: {len(settings.VK_GROUP_TOKEN)} символов")
    if settings.VK_USER_TOKEN:
        logger.info(f"Длина пользовательского токена: {len(settings.VK_USER_TOKEN)} символов")

    # Проверяем, похожи ли токены на настоящие
    if settings.VK_GROUP_TOKEN and settings.VK_GROUP_TOKEN == "your_group_token_here":
        logger.error("Групповой токен не настроен! Укажите настоящий токен в .env файле")
        return

    if settings.VK_USER_TOKEN and settings.VK_USER_TOKEN == "your_user_token_here":
        logger.error("Пользовательский токен не настроен! Укажите настоящий токен в .env файле")
        return

    try:
        create_tables()  # Создаем новые
        logger.info("Новые таблицы созданы")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        return

    logger.info("Инициализация бота")

    try:
        # Передаем оба токена: групповой для бота и пользовательский для поиска
        bot = VkBot(settings.VK_GROUP_TOKEN, settings.VK_USER_TOKEN)
        logger.info("Бот инициализирован")
    except Exception as e:
        logger.error(f"Ошибка при инициализации бота: {e}")
        return

    logger.info("Запуск бота")
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")


if __name__ == "__main__":
    main()
