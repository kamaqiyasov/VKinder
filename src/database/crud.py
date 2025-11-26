from sqlalchemy.orm import Session
from src.database.models import User, Profile, UserAction, Blacklist, Gender, SearchGender, ActionType

def create_user(db: Session, vk_user_id: int, firstname: str, lastname: str,
                user_vk_link: str, age: int, gender: Gender, city: str):
    user = User(
        vk_user_id=vk_user_id,
        firstname=firstname,
        lastname=lastname,
        user_vk_link=user_vk_link,
        age=age,
        gender=gender,
        city=city
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_profile(db: Session, user_id: int, description: str, interests: list[str],
                   search_gender: SearchGender, search_age_min: int, search_age_max: int):
    profile = Profile(
        user_id=user_id,
        description=description,
        interests=interests,
        search_gender=search_gender,
        search_age_min=search_age_min,
        search_age_max=search_age_max
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile

def add_user_action(db: Session, user_id: int, target_user_id: int, action_type: ActionType):
    action = UserAction(
        user_id=user_id,
        target_user_id=target_user_id,
        action_type=action_type
    )
    db.add(action)
    db.commit()
    return action

def add_to_blacklist(db: Session, user_id: int, blocked_user_id: int):
    blacklist_entry = Blacklist(
        user_id=user_id,
        blocked_user_id=blocked_user_id
    )
    db.add(blacklist_entry)
    db.commit()
    return blacklist_entry