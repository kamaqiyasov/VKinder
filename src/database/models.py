import enum
from datetime import datetime
from sqlalchemy import BigInteger, Enum, Identity, Integer, String, Text, Boolean, DateTime, ForeignKey, ARRAY, \
    CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)


class Gender(enum.Enum):
    MALE = "Мужской"
    FEMALE = "Женский"


class SearchGender(enum.Enum):
    MALE = "male"
    FEMALE = "female"
    ANY = "any"


class ActionType(enum.Enum):
    LIKE = "like"
    DISLIKE = "dislike"
    VIEW = "view"
    SKIP = "skip"


class User(BaseModel):
    __tablename__ = "users"

    vk_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    firstname: Mapped[str] = mapped_column(String(50), nullable=False)
    lastname: Mapped[str] = mapped_column(String(50), nullable=False)
    user_vk_link: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[Gender] = mapped_column(Enum(Gender))
    city: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

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
    search_gender: Mapped[SearchGender] = mapped_column(Enum(SearchGender), nullable=False)
    search_age_min: Mapped[int] = mapped_column(Integer, nullable=False)
    search_age_max: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="profile")

    __table_args__ = (
        CheckConstraint('search_age_min >= 18', name='check_search_age_min'),
        CheckConstraint('search_age_max >= search_age_min', name='check_search_age_range'),
    )


class UserAction(BaseModel):
    __tablename__ = "user_actions"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    target_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    action_type: Mapped[ActionType] = mapped_column(Enum(ActionType), nullable=False)
    action_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Связи
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="actions")
    target_user: Mapped["User"] = relationship("User", foreign_keys=[target_user_id])

    __table_args__ = (
        UniqueConstraint('user_id', 'target_user_id', 'action_type', name='uq_user_action'),
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