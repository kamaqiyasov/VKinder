import enum
import json

from datetime import datetime
from sqlalchemy import BigInteger, Enum, Identity, Integer, String, Text, Boolean, DateTime, ForeignKey, ARRAY, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, declarative_base


Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)


class User(BaseModel):
    __tablename__ = "users"

    vk_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    user_vk_link: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    city: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        CheckConstraint(
            gender.in_(['Мужской', 'Женский']), 
            name='valid_gender'
        ),
    )

    # Связи
    profile: Mapped["Profile"] = relationship("Profile", back_populates="user", uselist=False)
    actions: Mapped[list["UserAction"]] = relationship("UserAction", foreign_keys="[UserAction.user_id]",
                                                       back_populates="user")
    blacklists: Mapped[list["Blacklist"]] = relationship("Blacklist", foreign_keys="[Blacklist.user_id]",
                                                         back_populates="user")


class Profile(BaseModel):
    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    interests: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    search_gender: Mapped[str] = mapped_column(String(10), nullable=False)
    search_age_min: Mapped[int] = mapped_column(Integer, nullable=False)
    search_age_max: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="profile")

    __table_args__ = (
        CheckConstraint('search_age_min >= 18', name='check_search_age_min'),
        CheckConstraint('search_age_max >= search_age_min', name='check_search_age_range'),
        CheckConstraint(
            search_gender.in_(['male', 'female', 'any']), 
            name='valid_seatch_gender'
            )
    )


class UserAction(BaseModel):
    __tablename__ = "user_actions"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    target_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(10), nullable=False)
    action_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Связи
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="actions")
    target_user: Mapped["User"] = relationship("User", foreign_keys=[target_user_id])

    __table_args__ = (
        UniqueConstraint('user_id', 'target_user_id', 'action_type', name='uq_user_action'),
        CheckConstraint(
            action_type.in_(['like', 'dislike', 'view', 'skip']),
            name='valid_action_type'
        )
    )


class Blacklist(BaseModel):
    __tablename__ = "blacklist"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    blocked_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Связи
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="blacklists")
    blocked_user: Mapped["User"] = relationship("User", foreign_keys=[blocked_user_id])

    __table_args__ = (
        UniqueConstraint('user_id', 'blocked_user_id', name='uq_blacklist'),
        CheckConstraint('user_id != blocked_user_id', name='check_no_self_block'),
    )
    city: Mapped[str] = mapped_column(String, nullable=False)
    
class UserState(Base):
    __tablename__ = "user_states"
    
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    state: Mapped[str] = mapped_column(String(100), nullable=True)
    data: Mapped[str] = mapped_column(Text, default="{}")
    
    def get_data(self) -> dict:
        return json.loads(self.data) if self.data else {}
    
    def set_data(self, data: dict):
        self.data = json.dumps(data, ensure_ascii=False)
