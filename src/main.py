from src.config import settings
from src.database.base import create_tables, drop_tables
from src.vk_bot.vk_bot import VkBot


def main():
    drop_tables()
    if not create_tables():
        return
    
    bot = VkBot(settings.VK_TOKEN)
    bot.run()

if __name__ == "__main__":
    main()
    