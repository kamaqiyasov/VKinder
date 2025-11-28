from sqlalchemy.orm import Session
from src.database.models import BotUser, UserState, Profile, Photo, Favorite, Blacklist, SearchPreferences
from typing import List, Optional, Dict

# ==================== Операции с пользователями ====================

def get_bot_user(db: Session, bot_user_id: int) -> Optional[BotUser]:
    # Получить пользователя бота по ID
    return db.query(BotUser).filter(BotUser.id == bot_user_id).first()

def get_bot_user_by_vk_id(db: Session, vk_id: int) -> Optional[BotUser]:
    # Получить пользователя бота по VK ID
    return db.query(BotUser).filter(BotUser.vk_id == vk_id).first()

def create_or_update_bot_user(db: Session, vk_id: int, first_name: str, last_name: str,
                              age: int = None, sex: int = None, city: str = None) -> BotUser:
    # Создать или обновить пользователя бота
    existing_user = db.query(BotUser).filter(BotUser.vk_id == vk_id).first()

    if existing_user:
        # Обновляем существующего пользователя
        existing_user.first_name = first_name
        existing_user.last_name = last_name
        if age is not None:
            existing_user.age = age
        if sex is not None:
            existing_user.sex = sex
        if city is not None:
            existing_user.city = city
    else:
        # Создаем нового пользователя
        existing_user = BotUser(
            vk_id=vk_id,
            first_name=first_name,
            last_name=last_name,
            age=age,
            sex=sex,
            city=city
        )
        db.add(existing_user)

    db.commit()
    db.refresh(existing_user)
    return existing_user

def delete_bot_user(db: Session, bot_user_id: int) -> bool:
    # Удалить пользователя бота
    user = db.query(BotUser).filter(BotUser.id == bot_user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return True
    return False

# ==================== Операции с состояниями ====================

def get_user_state(db: Session, vk_id: int) -> Optional[UserState]:
    # Получить состояние пользователя
    return db.query(UserState).filter(UserState.vk_id == vk_id).first()

def create_or_update_user_state(db: Session, vk_id: int, state: str, state_data: Dict = None) -> UserState:
    # Создать или обновить состояние пользователя
    existing_state = db.query(UserState).filter(UserState.vk_id == vk_id).first()

    if existing_state:
        existing_state.current_state = state
        if state_data is not None:
            existing_state.state_data = state_data
    else:
        existing_state = UserState(
            vk_id=vk_id,
            current_state=state,
            state_data=state_data or {}
        )
        db.add(existing_state)

    db.commit()
    db.refresh(existing_state)
    return existing_state

def update_user_state_data(db: Session, vk_id: int, **kwargs) -> Optional[UserState]:
    # Обновить данные состояния пользователя
    state = db.query(UserState).filter(UserState.vk_id == vk_id).first()
    if state:
        current_data = state.state_data or {}
        current_data.update(kwargs)
        state.state_data = current_data
        db.commit()
        db.refresh(state)
    return state

def delete_user_state(db: Session, vk_id: int) -> bool:
    # Удалить состояние пользователя
    state = db.query(UserState).filter(UserState.vk_id == vk_id).first()
    if state:
        db.delete(state)
        db.commit()
        return True
    return False

# ==================== Операции с профилями ====================

def get_profile(db: Session, profile_id: int) -> Optional[Profile]:
    # Получить профиль по ID
    return db.query(Profile).filter(Profile.id == profile_id).first()

def get_profile_by_vk_id(db: Session, vk_id: int) -> Optional[Profile]:
    # Получить профиль по VK ID
    return db.query(Profile).filter(Profile.vk_id == vk_id).first()

def create_or_update_profile(db: Session, vk_id: int, first_name: str, last_name: str,
                             profile_url: str = None, age: int = None, sex: int = None,
                             city: str = None) -> Profile:
    # Создать или обновить профиль
    existing_profile = db.query(Profile).filter(Profile.vk_id == vk_id).first()

    if existing_profile:
        existing_profile.first_name = first_name
        existing_profile.last_name = last_name
        if profile_url is not None:
            existing_profile.profile_url = profile_url
        if age is not None:
            existing_profile.age = age
        if sex is not None:
            existing_profile.sex = sex
        if city is not None:
            existing_profile.city = city
    else:
        existing_profile = Profile(
            vk_id=vk_id,
            first_name=first_name,
            last_name=last_name,
            profile_url=profile_url,
            age=age,
            sex=sex,
            city=city
        )
        db.add(existing_profile)

    db.commit()
    db.refresh(existing_profile)
    return existing_profile

def delete_profile(db: Session, profile_id: int) -> bool:
    # Удалить профиль
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if profile:
        db.delete(profile)
        db.commit()
        return True
    return False

def find_profiles_by_criteria(db: Session, city: str = None, age_min: int = None,
                              age_max: int = None, sex: int = None, exclude_vk_ids: List[int] = None) -> List[Profile]:
    # Найти профили по критериям
    query = db.query(Profile)

    if city:
        query = query.filter(Profile.city == city)
    if age_min is not None:
        query = query.filter(Profile.age >= age_min)
    if age_max is not None:
        query = query.filter(Profile.age <= age_max)
    if sex is not None:
        query = query.filter(Profile.sex == sex)
    if exclude_vk_ids:
        query = query.filter(Profile.vk_id.notin_(exclude_vk_ids))

    return query.all()

# ==================== Операции с фотографиями ====================

def add_photos_to_profile(db: Session, profile_id: int, photos: List[Dict]) -> List[Photo]:
    # Добавить фотографии к профилю
    db.query(Photo).filter(Photo.profile_id == profile_id).delete() # Удаляем старые фотографи

    # Добавляем новые
    photo_objects = []
    for photo_data in photos:
        photo = Photo(
            profile_id=profile_id,
            photo_url=photo_data['url'],
            likes_count=photo_data.get('likes', 0)
        )
        db.add(photo)
        photo_objects.append(photo)

    db.commit()

    # Обновляем ID для всех объектов
    for photo in photo_objects:
        db.refresh(photo)

    return photo_objects

def get_profile_photos(db: Session, profile_id: int) -> List[Photo]:
    # Получить фотографии профиля
    return db.query(Photo).filter(Photo.profile_id == profile_id).order_by(Photo.likes_count.desc()).all()

def get_top_profile_photos(db: Session, profile_id: int, limit: int = 3) -> List[Photo]:
    # Получить топ-фотографии профиля
    return db.query(Photo).filter(Photo.profile_id == profile_id).order_by(Photo.likes_count.desc()).limit(limit).all()

# ==================== Операции с избранными  ====================

def add_to_favorites(db: Session, bot_user_id: int, profile_id: int) -> Favorite:
    # Добавить профиль в избранное
    favorite = Favorite(
        bot_user_id=bot_user_id,
        profile_id=profile_id
    )
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite

def get_favorites(db: Session, bot_user_id: int) -> List[Profile]:
    # Получить избранные профили пользователя
    favorites = db.query(Favorite).filter(Favorite.bot_user_id == bot_user_id).all()
    return [favorite.profile for favorite in favorites]

def remove_from_favorites(db: Session, bot_user_id: int, profile_id: int) -> bool:
    # Удалить профиль из избранного
    favorite = db.query(Favorite).filter(
        Favorite.bot_user_id == bot_user_id,
        Favorite.profile_id == profile_id
    ).first()

    if favorite:
        db.delete(favorite)
        db.commit()
        return True
    return False

def is_in_favorites(db: Session, bot_user_id: int, profile_id: int) -> bool:
    # Проверить, находится ли профиль в избранном
    return db.query(Favorite).filter(
        Favorite.bot_user_id == bot_user_id,
        Favorite.profile_id == profile_id
    ).first() is not None

# ==================== Операции с черным списком  ====================

def add_to_blacklist(db: Session, bot_user_id: int, profile_id: int) -> Blacklist:
    # Добавить профиль в черный список
    blacklist = Blacklist(
        bot_user_id=bot_user_id,
        profile_id=profile_id
    )
    db.add(blacklist)
    db.commit()
    db.refresh(blacklist)
    return blacklist

def get_blacklist(db: Session, bot_user_id: int) -> List[Profile]:
    # Получить черный список пользователя
    blacklist_entries = db.query(Blacklist).filter(Blacklist.bot_user_id == bot_user_id).all()
    return [entry.profile for entry in blacklist_entries]

def remove_from_blacklist(db: Session, bot_user_id: int, profile_id: int) -> bool:
    # Удалить профиль из черного списка
    blacklist = db.query(Blacklist).filter(
        Blacklist.bot_user_id == bot_user_id,
        Blacklist.profile_id == profile_id
    ).first()

    if blacklist:
        db.delete(blacklist)
        db.commit()
        return True
    return False

def is_in_blacklist(db: Session, bot_user_id: int, profile_id: int) -> bool:
    # Проверить, находится ли профиль в черном списке
    return db.query(Blacklist).filter(
        Blacklist.bot_user_id == bot_user_id,
        Blacklist.profile_id == profile_id
    ).first() is not None

# ==================== Операции с поиском ====================

def get_search_preferences(db: Session, bot_user_id: int) -> Optional[SearchPreferences]:
    # Получить поисковые предпочтения пользователя
    return db.query(SearchPreferences).filter(SearchPreferences.bot_user_id == bot_user_id).first()

def create_or_update_search_preferences(db: Session, bot_user_id: int, search_sex: int = None,
                                        search_age_min: int = None, search_age_max: int = None,
                                        search_city: str = None) -> SearchPreferences:
    # Создать или обновить поисковые предпочтения
    preferences = db.query(SearchPreferences).filter(SearchPreferences.bot_user_id == bot_user_id).first()

    if preferences:
        if search_sex is not None:
            preferences.search_sex = search_sex
        if search_age_min is not None:
            preferences.search_age_min = search_age_min
        if search_age_max is not None:
            preferences.search_age_max = search_age_max
        if search_city is not None:
            preferences.search_city = search_city
    else:
        preferences = SearchPreferences(
            bot_user_id=bot_user_id,
            search_sex=search_sex,
            search_age_min=search_age_min,
            search_age_max=search_age_max,
            search_city=search_city
        )
        db.add(preferences)

    db.commit()
    db.refresh(preferences)
    return preferences

def delete_search_preferences(db: Session, bot_user_id: int) -> bool:
    # Удалить поисковые предпочтения пользователя
    preferences = db.query(SearchPreferences).filter(SearchPreferences.bot_user_id == bot_user_id).first()
    if preferences:
        db.delete(preferences)
        db.commit()
        return True
    return False