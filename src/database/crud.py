from src.database.base import Session
from src.database.models import BotUser


def get_user_by_vk_id(vk_id: int) -> BotUser | None:
    with Session() as session:
        return session.query(BotUser).filter_by(vk_id=vk_id).first()

def save_user_from_vk(vk_id: int, first_name: str, last_name: str, vk_link: str, age: int, sex: str, city: str) -> BotUser:
    with Session() as session:
        user = session.query(BotUser).filter_by(vk_id=vk_id).first()
        if user:
            user.first_name = first_name
            user.last_name = last_name
            user.user_vk_link = vk_link
            user.age = age
            user.sex = sex
            user.city = city
        else:
            if sex == 'Женский':
                sex: int = 1
            elif sex == 'Мужской':
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