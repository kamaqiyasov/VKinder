from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.database.models import Base

engine = create_engine(
    url=settings.DATABASE_URL_psycopg,
)

Session = sessionmaker(bind=engine)

def check_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Ошибка соеденения с БД: {e}")
        return False

def create_tables():
    if check_connection():
        Base.metadata.create_all(engine)
        return True
    return False
    
def drop_tables():
    if check_connection():
        Base.metadata.drop_all(engine)
        return True
    return False