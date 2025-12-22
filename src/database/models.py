import json
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


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
    favorites = relationship('Favorite', back_populates='bot_user')
    blacklist = relationship('Blacklist', back_populates='bot_user')
    search_preferences = relationship('SearchPreferences', back_populates='bot_user', uselist=False)


class UserState(Base):
    __tablename__ = "user_states"

    id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, nullable=False)
    state = Column(String(100), nullable=True)
    data = Column(Text, default="{}")

    @property
    def current_state(self):
        """Геттер для совместимости с существующим кодом"""
        return self.state

    @current_state.setter
    def current_state(self, value):
        """Сеттер для совместимости с существующим кодом"""
        self.state = value

    @property
    def state_data(self):
        """Геттер для совместимости с существующим кодом"""
        return json.loads(self.data) if self.data else {}

    @state_data.setter
    def state_data(self, value):
        """Сеттер для совместимости с существующим кодом"""
        self.data = json.dumps(value, ensure_ascii=False)

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
    interests = Column(Text)

    # Отношения
    photos = relationship('Photo', back_populates='profile')
    favorites = relationship('Favorite', back_populates='profile')
    blacklist = relationship('Blacklist', back_populates='profile')

    __table_args__ = (
        Index('idx_profile_city', 'city'),
        Index('idx_profile_age', 'age'),
        Index('idx_profile_sex', 'sex'),
    )

    __table_args__ = (
        Index('idx_profile_city', 'city'),
        Index('idx_profile_age', 'age'),
        Index('idx_profile_sex', 'sex'),
    )


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


class ViewedProfiles(Base):
    __tablename__ = 'viewed_profiles'

    id = Column(Integer, primary_key=True)
    bot_user_id = Column(Integer, ForeignKey('bot_users.id'))
    profile_id = Column(Integer, ForeignKey('profiles.id'))
    viewed_at = Column(DateTime, default=func.now())

    # Отношения
    bot_user = relationship("BotUser",)
    profile = relationship("Profile")

    # Уникальность
    __table_args__ = (UniqueConstraint('bot_user_id', 'profile_id', name='uq_viewed_profiles_user_profile'),)

class PhotoLike(Base):
    __tablename__ = 'photo_likes'

    id = Column(Integer, primary_key=True)
    bot_user_id = Column(Integer, ForeignKey('bot_users.id'))
    photo_url = Column(String(500), nullable=False)
    profile_id = Column(Integer, ForeignKey('profiles.id'))
    liked_at = Column(DateTime, default=func.now())

    # Отношения
    bot_user = relationship("BotUser")
    profile = relationship("Profile")

    __table_args__ = (
        UniqueConstraint('bot_user_id', 'photo_url', name='uq_photo_like_user_photo'),
    )
