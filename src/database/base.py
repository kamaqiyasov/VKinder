from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.database.models import Base

class  DatabaseManager:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL_psycopg)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        # Создание всех таблиц
        Base.metadata.create_all(self.engine)
        print("Все таблицы созданы")

    def drop_tables(self):
        # Удаление всех таблиц
        Base.metadata.drop_all(self.engine)
        print("Все таблицы удалены")

    def get_session(self):
        # Получение сессии для работы с БД
        return self.Session()

#
db_manager = DatabaseManager()
def create_tables():
    db_manager.create_tables()
    return True

def drop_tables():
    db_manager.drop_tables()
    return True

def Session():
    # Получение сессии для работы с БД
    return db_manager.get_session()