from sqlalchemy import Text, UniqueConstraint, create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List

class Base(DeclarativeBase):
    pass


class BotUser(Base):
    __tablename__ = 'bot_users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    vk_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(50))
    last_name: Mapped[Optional[str]] = mapped_column(String(50))
    age: Mapped[Optional[int]]
    sex: Mapped[Optional[int]]
    city: Mapped[Optional[str]] = mapped_column(String(100))
    access_token: Mapped[Optional[str]] = mapped_column(Text)
    
    search_settings: Mapped["SearchSettings"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    interactions: Mapped[List["UserInteraction"]] = relationship(back_populates="bot_user", cascade="all, delete-orphan")


class UserInteraction(Base):
    __tablename__ = 'user_interactions'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    bot_user_id: Mapped[int] = mapped_column(ForeignKey('bot_users.id', ondelete='CASCADE'))
    vk_id: Mapped[int] = mapped_column(nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(20))
    interaction_date: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    vk_name: Mapped[Optional[str]] = mapped_column(String(100))
    profile_link: Mapped[Optional[str]] = mapped_column(String(200))
    photos: Mapped[Optional[dict]] = mapped_column(JSON)
    
    bot_user: Mapped["BotUser"] = relationship(back_populates="interactions")
    
    __table_args__ = (
        UniqueConstraint('bot_user_id', 'vk_id', 'interaction_type'),
    )
    
    
class SearchSettings(Base):
    __tablename__ = 'search_settings'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    bot_user_id: Mapped[int] = mapped_column(ForeignKey('bot_users.id', ondelete='CASCADE'), unique=True)
    age_from: Mapped[int] = mapped_column(default=18)
    sex: Mapped[Optional[int]]  # 1 - жен, 2 - муж    
    age_to: Mapped[int] = mapped_column(default=35)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    has_photo: Mapped[bool] = mapped_column(default=True)
    status: Mapped[Optional[int]]
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user: Mapped["BotUser"] = relationship(back_populates="search_settings")