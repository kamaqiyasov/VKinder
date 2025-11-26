import enum
import json
from sqlalchemy import BigInteger, Enum, Identity, Integer, String, Text
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
    
class UserState(Base):
    __tablename__ = "user_states"
    
    user_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    state: Mapped[str] = mapped_column(String(100), nullable=True)
    data: Mapped[str] = mapped_column(Text, default="{}")
    
    def get_data(self) -> dict:
        return json.loads(self.data) if self.data else {}
    
    def set_data(self, data: dict):
        self.data = json.dumps(data, ensure_ascii=False)