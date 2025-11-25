from sqlalchemy import select
from src.database.base import Session
from src.database.models import Gender, User


def user_exists(user_id: int) -> bool:
    """Проверка на существование пользователя в бд

    Args:
        user_id (int): user_id пользователя VK

    Returns:
        bool: True - если пользователь есть, False - если нет пользователя
    """
    with Session() as session:
        stmt = select(User).where(User.vk_user_id == user_id)
        res = session.execute(stmt)
        
        return res.first() is not None

def create_user(
    vk_user_id: int, 
    firstname: str, 
    lastname: str, 
    user_vk_link: str, 
    age: int, 
    gender: str,
    city: str) -> User:
    """Добавление нового пользователя в бд

    Args:
        vk_user_id (int): ID пользотвалея VK
        firstname (str): Имя
        lastname (str): Фамилия
        user_vk_link (str): Ссылка на страницу пользователя
        age (int): Возраст
        gender (Gender): Пол
        city (str): Город

    Returns:
        User: объект класса User
    """
    if gender.lower() == "мужской":
        gender_enum = Gender.MALE
    elif gender.lower() == "женский":
        gender_enum = Gender.FEMALE
    else:
        raise ValueError("Неверный пол")
    
    with Session() as session:
        user = User(
            vk_user_id=vk_user_id,
            firstname=firstname,
            lastname=lastname,
            user_vk_link=user_vk_link,
            age=age,
            gender=gender_enum,
            city=city
        )
        session.add(user)
        session.commit()
        
        return user