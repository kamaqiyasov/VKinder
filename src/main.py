import logging

from src.config import settings
from src.database.base import create_tables, drop_tables
from src.vk_bot.vk_bot import VkBot


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Запуск программы")
    
    logger.info("Сбрасываем таблицы БД")
    drop_tables()
    
    logger.info("Создаём таблицы БД")
    if not create_tables():
        logger.error("Не удалось создать таблицы")
        return
    
    logger.info("Инициализация бота")
    bot = VkBot(settings.VK_TOKEN)
    
    logger.info("Запуск бота")
    bot.run()

if __name__ == "__main__":
    main()
    