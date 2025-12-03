from src.database.base import Session
from src.database.models import BotUser


def get_user_by_vk_id(vk_id: int) -> BotUser | None:
    with Session() as session:
        return session.query(BotUser).filter_by(vk_id=vk_id).first()

def save_user_from_vk(vk_id: int, first_name: str = None, last_name: str = None, age: int = None, sex: int = None, city: str = None) -> BotUser:
    with Session() as session:
        user = session.query(BotUser).filter_by(vk_id=vk_id).first()
        if user:
            user.first_name = first_name
            user.last_name = last_name
            user.user_vk_link = vk_link
            user.age = age
            user.sex = gender
            user.city = city
        else:
            if gender == 'Женский':
                sex: int = 1
            elif gender == 'Мужской':
                sex: int = 2
            
            user = BotUser(
                vk_id=vk_id,
                first_name=first_name,
                last_name=last_name,
                user_vk_link=vk_link,
                age=age,
                sex=sex,
                city=city
            )
            session.add(user)
            
        session.commit()
        session.refresh(user)
        return user