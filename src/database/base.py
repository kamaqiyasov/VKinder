import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.database.models import Base


logger = logging.getLogger(__name__)

class  DatabaseManager:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL_psycopg)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def check_connection(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Успешное подключение к БД")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            return False    
        
    def create_tables(self) -> bool:
        # Создание всех таблиц        
        if self.check_connection():
            try:
                Base.metadata.create_all(self.engine)
                logger.info("Таблицы созданы")
                return True
            except Exception as e:
                logger.error(f"Ошибка создания таблиц: {e}")
                return False
        return False
    
    def drop_tables(self) -> bool:
        # Удаление всех таблиц
        if self.check_connection():
            try:
                Base.metadata.drop_all(self.engine)
                logger.info("Таблицы удалены")
                return True
            except Exception as e:
                logger.error(f"Ошибка удаления таблиц: {e}")
                return False
        return False
    
    def get_session(self):
        # Получение сессии для работы с БД
        return self.Session()
    
db_manager = DatabaseManager()
def create_tables():
    return db_manager.create_tables()
    
def drop_tables():
    return db_manager.drop_tables()

def Session():
    # Получение сессии для работы с БД
    return db_manager.get_session()