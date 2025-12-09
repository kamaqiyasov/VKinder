from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from src.config import settings
from src.database.models import Base

class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(
            settings.DATABASE_URL_psycopg,
            pool_size=10,           # Уменьшаем размер пула
            max_overflow=20,        # Увеличиваем переполнение
            pool_pre_ping=True,     # Проверка соединений
            pool_recycle=3600,      # Пересоздание соединений через час
            pool_timeout=30,        # Таймаут соединения
            echo=settings.DEBUG     # Логирование SQL запросов в debug режиме
        )
        self.Session = scoped_session(sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        ))

    def create_tables(self):
        Base.metadata.create_all(self.engine)
        print("Все таблицы созданы")

    def drop_tables(self):
        Base.metadata.drop_all(self.engine)
        print("Все таблицы удалены")

    def get_session(self):
        return self.Session()

# Глобальный менеджер базы данных
db_manager = DatabaseManager()

def create_tables():
    db_manager.create_tables()
    return True

def drop_tables():
    db_manager.drop_tables()
    return True

def Session():
    return db_manager.get_session()