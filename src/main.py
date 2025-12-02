import logging
from src.config import settings
from src.vk_bot.vk_bot import VkBot
from src.database.base import create_tables, drop_tables

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Запуск программы")

    # Пересоздаем таблицы с исправленными моделями
    try:
        drop_tables()  # Удаляем старые таблицы
        logger.info("Старые таблицы удалены")
        create_tables()  # Создаем новые
        logger.info("Новые таблицы созданы")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        return

    logger.info("Инициализация бота")

    try:
        bot = VkBot(settings.VK_TOKEN)
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