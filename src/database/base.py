import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.database.models import Base


logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL_psycopg)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Создает все таблицы в базе данных"""
    Base.metadata.create_all(bind=engine)
    logger.info("Таблицы созданы")

def drop_tables():
    """Удаляет все таблицы из базы данных"""
    Base.metadata.drop_all(bind=engine)
    logger.info("Таблицы удалены")
