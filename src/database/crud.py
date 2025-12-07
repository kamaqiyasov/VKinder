from typing import List, Optional
from src.database.base import SessionLocal
from src.database.models import BotUser, SearchSettings, UserInteraction

def save_user_with_token(vk_id: int, token: str, user_info: dict) -> bool:
    with SessionLocal() as db:
        user = db.query(BotUser).filter_by(vk_id=vk_id).first()
        
        if not user:
            user = BotUser(
                vk_id=vk_id,
                first_name=user_info.get('first_name'),
                last_name=user_info.get('last_name'),
                age=user_info['age'],
                sex=user_info['sex'],
                city=user_info['city'],
                access_token=token
            )
            db.add(user)
        else:
            user.first_name = user_info.get('first_name')
            user.last_name = user_info.get('last_name')
            user.age = user_info['age']
            user.sex = user_info['sex']
            user.city = user_info['city']
            user.access_token = token
        
        try:
            db.commit()
            return True
        except:
            db.rollback()
            return False

def get_user_token(vk_id: int) -> Optional[str]:
    """Получает токен пользователя из БД"""
    with SessionLocal() as db:
        user = db.query(BotUser).filter_by(vk_id=vk_id).first()
        return user.access_token if user else None
    
def get_user_by_vk_id(vk_id: int) -> Optional[BotUser]:
    """Получает пользователя по VK ID"""
    with SessionLocal() as db:
        return db.query(BotUser).filter_by(vk_id=vk_id).first()
    
def get_or_create_search_settings(vk_user_id: int, age: Optional[int] = None, city: Optional[str] = None, sex: Optional[int] = None) -> Optional[SearchSettings]:
    """Получает или создает настройки поиска"""
    with SessionLocal() as db:
        user = db.query(BotUser).filter_by(id=vk_user_id).first()
        if not user:
            return None
        
        settings = db.query(SearchSettings).filter_by(bot_user_id=user.id).first()
        if not settings:
            settings = SearchSettings(
                bot_user_id=user.id,
                age_from=age-3 if age else 18,
                age_to=age+3 if age else 35,
                city=city,
                sex=sex
            )
            db.add(settings)
            db.commit()
        
        return settings
    
def update_search_settings(vk_user_id: int, **kwargs) -> bool:
    """Обновляет настройки поиска"""
    with SessionLocal() as db:
        user = db.query(BotUser).filter_by(id=vk_user_id).first()
        if not user:
            return False
        
        settings = db.query(SearchSettings).filter_by(bot_user_id=user.id).first()
        if not settings:
            return False
        
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        db.commit()
        return True
    
def add_interaction(bot_user_id: int, vk_id: int, interaction_type: str, **data) -> bool:
    """Добавляет взаимодействие (просмотр/избранное/ЧС)"""
    with SessionLocal() as db:
        try:
            interaction = UserInteraction(
                bot_user_id=bot_user_id,
                vk_id=vk_id,
                interaction_type=interaction_type,
                vk_name=data.get('vk_name'),
                profile_link=data.get('profile_link'),
                photos=data.get('photos')
            )
            db.add(interaction)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            return False

def get_interactions(bot_user_id: int, interaction_type: Optional[str] = None) -> List[UserInteraction]:
    """Получает взаимодействия пользователя"""
    with SessionLocal() as db:
        query = db.query(UserInteraction).filter_by(bot_user_id=bot_user_id)
        
        if interaction_type:
            query = query.filter_by(interaction_type=interaction_type)
        
        return query.all()

def is_interaction_exists(bot_user_id: int, vk_id: int, interaction_type: str) -> bool:
    """Проверяет существование взаимодействия"""
    with SessionLocal() as db:
        interaction = db.query(UserInteraction).filter_by(
            bot_user_id=bot_user_id,
            vk_id=vk_id,
            interaction_type=interaction_type
        ).first()
        return interaction is not None
    
def get_favorites(bot_user_id: int) -> List[UserInteraction]:
    """Получает избранные пользователей"""
    return get_interactions(bot_user_id, interaction_type='favorite')

def get_blacklist(bot_user_id: int) -> List[UserInteraction]:
    """Получает черный список"""
    return get_interactions(bot_user_id, interaction_type='blacklist')

def remove_from_favorites(bot_user_id: int, vk_id: int) -> bool:
    """Удаляет из избранного"""
    with SessionLocal() as db:
        interaction = db.query(UserInteraction).filter_by(
            bot_user_id=bot_user_id,
            vk_id=vk_id,
            interaction_type='favorite'
        ).first()
        
        if interaction:
            db.delete(interaction)
            db.commit()
            return True
        return False
    
def remove_from_blacklist(bot_user_id: int, vk_id: int) -> bool:
    """Удаляет из черного списка"""
    with SessionLocal() as db:
        interaction = db.query(UserInteraction).filter_by(
            bot_user_id=bot_user_id,
            vk_id=vk_id,
            interaction_type='blacklist'
        ).first()
        
        if interaction:
            db.delete(interaction)
            db.commit()
            return True
        return False