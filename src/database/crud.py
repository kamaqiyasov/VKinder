from src.database.base import Session
from src.database.models import User, Profile, UserAction, Blacklist

def get_user_by_vk_id(vk_user_id: int) -> User | None:
    with Session() as session:
        return session.query(User).filter_by(vk_user_id=vk_user_id).first()

def save_user_from_vk(vk_user_id: int, first_name: str, last_name: str, vk_link: str, age: int, gender: str, city: str) -> User:
    with Session() as session:
        user = session.query(User).filter_by(vk_user_id=vk_user_id).first()
        if user:
            user.first_name = first_name
            user.last_name = last_name
            user.user_vk_link = vk_link
            user.age = age
            user.gender = gender
            user.city = city
        else:
            user = User(
                vk_user_id=vk_user_id,
                first_name=first_name,
                last_name=last_name,
                user_vk_link=vk_link,
                age=age,
                gender=gender,
                city=city
            )
            session.add(user)
            
        session.commit()
        session.refresh(user)
        return user

def create_profile(db: Session, user_id: int, description: str, interests: list[str],
                   search_gender: str, search_age_min: int, search_age_max: int):
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

def add_user_action(db: Session, user_id: int, target_user_id: int, action_type: str):
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