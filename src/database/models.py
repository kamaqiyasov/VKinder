from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class Gender(enum.Enum):
    FEMALE = 1
    MALE = 2

class SearchGender(enum.Enum):
    FEMALE = 1
    MALE = 2
    ALL = 3

class BotUser(Base):
    __tablename__ = 'bot_users'

    id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, unique=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    age = Column(Integer)
    sex = Column(Integer)
    city = Column(String(100))

    # Отношения
    favorites = relationship('Favorite', back_populates='bot_user', cascade="all, delete-orphan")
    blacklist = relationship('Blacklist', back_populates='bot_user', cascade="all, delete-orphan")
    search_preferences = relationship('SearchPreferences', back_populates='bot_user', uselist=False, cascade="all, delete-orphan")

class UserState(Base):
    __tablename__ = 'user_states'

    id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, unique=True, nullable=False)
    current_state = Column(String(50), default='start')
    state_data = Column(JSON, default={})
    updated_at = Column(DateTime, default=func.now())

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
    photos = relationship('Photo', back_populates='profile', cascade="all, delete-orphan")
    favorites = relationship('Favorite', back_populates='profile', cascade="all, delete-orphan")
    blacklist_entries = relationship('Blacklist', back_populates='profile', cascade="all, delete-orphan")

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

    # Уникальность пары пользователь-профиль
    __table_args__ = (UniqueConstraint('bot_user_id', 'profile_id', name='uq_favorites_user_profile'),)

class Blacklist(Base):
    __tablename__ = 'blacklist'

    id = Column(Integer, primary_key=True)
    bot_user_id = Column(Integer, ForeignKey('bot_users.id'))
    profile_id = Column(Integer, ForeignKey('profiles.id'))
    added_at = Column(DateTime, default=func.now())

    # Отношения
    bot_user = relationship("BotUser", back_populates="blacklist")
    profile = relationship("Profile", back_populates="blacklist_entries")

    # Уникальность пары пользователь-профиль - ИСПРАВЛЕННЫЙ СИНТАКСИС
    __table_args__ = (UniqueConstraint('bot_user_id', 'profile_id', name='uq_blacklist_user_profile'),)

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