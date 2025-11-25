import enum
from sqlalchemy import BigInteger, Enum, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import declarative_base


Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)

class Gender(enum.Enum):
    MALE = "Мужской"
    FEMALE = "Женский"

class User(BaseModel):
    __tablename__ = "user"
    
    vk_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    firstname: Mapped[str] = mapped_column(String, nullable=False)
    lastname: Mapped[str] = mapped_column(String, nullable=False)
    user_vk_link: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[Gender] = mapped_column(Enum(Gender))
    city: Mapped[str] = mapped_column(String, nullable=False)