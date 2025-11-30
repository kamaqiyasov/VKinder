import logging
from src.config import settings
from src.vk_bot.vk_bot import VkBot
from src.database.base import db_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Запуск программы")
    db_manager.drop_tables()    
    if not db_manager.create_tables():
        return
    
    logger.info("Инициализация бота")
    bot = VkBot(settings.VK_TOKEN)
    
    logger.info("Запуск бота")
    bot.run()

if __name__ == "__main__":
    main()
    