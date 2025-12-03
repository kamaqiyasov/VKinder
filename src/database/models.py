import json
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class BotUser(Base):
    __tablename__ = 'bot_users'

    id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, unique=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    age = Column(Integer)
    sex = Column(Integer)  # 1 - жен, 2 - муж
    city = Column(String(100))
    user_vk_link = Column(String, nullable=False)
    
    # Отношения
    favorites = relationship('Favorite', back_populates='bot_user')
    blacklist = relationship('Blacklist', back_populates='bot_user')
    search_preferences = relationship('SearchPreferences', back_populates='bot_user', uselist=False)
    
    def is_profile_complete(self) -> bool:
        """
        Проверяет, заполнен ли профиль пользователя полностью.
        Обязательные поля: first_name, age, sex, city
        """
        # Проверяем, что все обязательные поля не None
        if self.first_name is None or (isinstance(self.first_name, str) and not self.first_name.strip()):
            return False
            
        if self.age is None or self.age <= 0 or self.age > 120:
            return False
            
        if self.sex is None or self.sex not in [1, 2]:  # 1 - жен, 2 - муж
            return False
            
        if self.city is None or (isinstance(self.city, str) and not self.city.strip()):
            return False
            
        return True
    
    def get_profile_summary(self) -> str:
        """Возвращает текстовое описание профиля"""
        if not self.is_profile_complete():
            return "Профиль не заполнен"
            
        sex_str = "женский" if self.sex == 1 else "мужской"
        last_name = f" {self.last_name}" if self.last_name else ""
        return (f"👤 {self.first_name}{last_name}\n"
                f"🎂 Возраст: {self.age}\n"
                f"🚻 Пол: {sex_str}\n"
                f"📍 Город: {self.city}")
    
    def get_sex_str(self) -> str:
        """Возвращает строковое представление пола"""
        if self.sex == 1:
            return "женский"
        elif self.sex == 2:
            return "мужской"
        return "не указан"
    
    
class UserState(Base):
    __tablename__ = "user_states"
    
    user_id = Column(Integer, primary_key=True)
    state = Column(String(100), nullable=True)
    data = Column(Text, default="{}")
    
    def get_data(self) -> dict:
        return json.loads(self.data) if self.data else {}
    
    def set_data(self, data: dict):
        self.data = json.dumps(data, ensure_ascii=False)

class Profile(Base):
    __tablename__ = 'profiles'

    id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, unique=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    profile_url = Column(String(255))
    age = Column(Integer)
    sex = Column(Integer)
    city = Column(String(100))

    # Отношения
    photos = relationship('Photo', back_populates='profile')
    favorites = relationship('Favorite', back_populates='profile')
    blacklist = relationship('Blacklist', back_populates='profile')

class Photo(Base):
    __tablename__ = 'photos'

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('profiles.id'))
    photo_url = Column(String(500), nullable=False)
    likes_count = Column(Integer, default=0)
    added_at = Column(DateTime, default=func.now())

    # Отношения
    profile = relationship("Profile", back_populates="photos")

class Favorite(Base):
    __tablename__ = 'favorites'

    id = Column(Integer, primary_key=True)
    bot_user_id = Column(Integer, ForeignKey('bot_users.id'))
    profile_id = Column(Integer, ForeignKey('profiles.id'))
    added_at = Column(DateTime, default=func.now())

    # Отношения
    bot_user = relationship("BotUser", back_populates="favorites")
    profile = relationship("Profile", back_populates="favorites")

class Blacklist(Base):
    __tablename__ = 'blacklist'

    id = Column(Integer, primary_key=True)
    bot_user_id = Column(Integer, ForeignKey('bot_users.id'))
    profile_id = Column(Integer, ForeignKey('profiles.id'))
    added_at = Column(DateTime, default=func.now())

    # Отношения
    bot_user = relationship("BotUser", back_populates="blacklist")
    profile = relationship("Profile", back_populates="blacklist")

class SearchPreferences(Base):
    __tablename__ = 'search_preferences'

    id = Column(Integer, primary_key=True)
    bot_user_id = Column(Integer, ForeignKey('bot_users.id'), unique=True)
    search_sex = Column(Integer)
    search_age_min = Column(Integer, default=18)
    search_age_max = Column(Integer, default=99)
    search_city = Column(String(100))
    updated_at = Column(DateTime, default=func.now())

    # Отношения
    bot_user = relationship("BotUser", back_populates="search_preferences")