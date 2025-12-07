import logging

import requests
from src.config import settings
from src.database.base import create_tables, drop_tables
from src.vk_bot.vk_bot import VkBot

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)-40s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler("vkinder.log", encoding="utf-8"),
                  logging.StreamHandler()])

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Запуск программы")

    # drop_tables()
    create_tables()
    
    # Запускаем бота
    bot = VkBot(settings.VK_GROUP_TOKEN, settings.VK_GROUP_ID)
    bot.run()

if __name__ == "__main__":
    main()
    