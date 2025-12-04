import logging
from src.config import settings
from src.vk_bot.vk_bot import VkBot
from src.database.base import create_tables, drop_tables

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
    drop_tables()    
    if not create_tables():
        return
    
    logger.info("Инициализация бота")
    bot = VkBot(settings.VK_TOKEN)
    
    logger.info("Запуск бота")
    bot.run()

if __name__ == "__main__":
    main()
    