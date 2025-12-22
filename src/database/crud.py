from sqlalchemy.orm import Session
from src.database.models import (
    BotUser, UserState, Profile, Photo, Favorite,
    Blacklist, SearchPreferences, ViewedProfiles,
    PhotoLike
)
from typing import List, Optional, Dict
import random


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


def save_user_from_vk(db: Session, vk_id: int, first_name: str, last_name: str,
                      age: int, sex: str, city: str) -> BotUser:
    # Сохраняем пользователя из VK
    sex_int = None

    if sex is not None:
        if isinstance(sex, int):
            sex_int = sex
        elif isinstance(sex, str):
            sex_lower = sex.lower()
            # Мужской пол
            if sex_lower in ["мужской", "male", "m", "2", "муж", "м"]:
                sex_int = 2
            # Женский пол
            elif sex_lower in ["женский", "female", "f", "1", "жен", "ж"]:
                sex_int = 1
            else:
                # Пытаемся преобразовать в число
                try:
                    sex_int = int(sex)
                    if sex_int not in [1, 2]:
                        sex_int = None
                except ValueError:
                    sex_int = None

    # Создаем или обновляем пользователя
    return create_or_update_bot_user(
        db=db,
        vk_id=vk_id,
        first_name=first_name,
        last_name=last_name,
        age=age,
        sex=sex_int,
        city=city
    )

# ==================== Операции с состояниями ====================


def get_user_state(db: Session, vk_id: int) -> Optional[UserState]:
    """Получить состояние пользователя"""
    return db.query(UserState).filter(UserState.vk_id == vk_id).first()


def create_or_update_user_state(db: Session, vk_id: int, state: str = None, state_data: Dict = None) -> UserState:
    """Создать или обновить состояние пользователя"""
    existing_state = db.query(UserState).filter(UserState.vk_id == vk_id).first()

    if existing_state:
        if state is not None:
            existing_state.current_state = state
        if state_data is not None:
            existing_state.set_data(state_data)
    else:
        existing_state = UserState(
            vk_id=vk_id
        )
        if state is not None:
            existing_state.current_state = state
        if state_data is not None:
            existing_state.set_data(state_data)
        db.add(existing_state)

    db.commit()
    db.refresh(existing_state)
    return existing_state


def update_user_state_data(db: Session, vk_id: int, **kwargs) -> Optional[UserState]:
    """Обновить данные состояния пользователя"""
    state = db.query(UserState).filter(UserState.vk_id == vk_id).first()
    if state:
        current_data = state.get_data()
        current_data.update(kwargs)
        state.set_data(current_data)
        db.commit()
        db.refresh(state)
    return state


def delete_user_state(db: Session, vk_id: int) -> bool:
    """Удалить состояние пользователя"""
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
    # Получаем текущие фото
    existing_photos = db.query(Photo).filter(
        Photo.profile_id == profile_id
    ).all()

    existing_urls = {p.photo_url for p in existing_photos}
    new_photos = []

    for photo_data in photos:
        photo_url = photo_data['url']

        # Если фото уже есть, обновляем лайки
        if photo_url in existing_urls:
            existing = db.query(Photo).filter(
                Photo.profile_id == profile_id,
                Photo.photo_url == photo_url
            ).first()
            if existing:
                existing.likes_count = photo_data.get('likes', existing.likes_count)
        else:
            # Добавляем новое фото
            photo = Photo(
                profile_id=profile_id,
                photo_url=photo_url,
                likes_count=photo_data.get('likes', 0)
            )
            db.add(photo)
            new_photos.append(photo)

    db.commit()
    return new_photos


def get_profile_photos(db: Session, profile_id: int) -> List[Photo]:
    # Получить фотографии профиля
    return db.query(Photo).filter(Photo.profile_id == profile_id).order_by(Photo.likes_count.desc()).all()


def get_top_profile_photos(db: Session, profile_id: int, limit: int = 3) -> List[Photo]:
    # Получить топ фотографии профиля
    return db.query(Photo).filter(
        Photo.profile_id == profile_id
    ).order_by(Photo.likes_count.desc()).limit(limit).all()

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

# ==================== Операции с поиском ====================


def save_search_results(db: Session, users: List[Dict]) -> List[Profile]:
    # Сохранить результаты в базу данных
    saved_profiles = []
    for user_data in users:
        # Проверяем, существует ли уже профиль с таким vk_id
        existing_profile = get_profile_by_vk_id(db, user_data['vk_id'])

        if existing_profile:
            # Если профиль уже существует, обновляем его
            existing_profile.first_name = user_data.get('first_name', existing_profile.first_name)
            existing_profile.last_name = user_data.get('last_name', existing_profile.last_name)
            existing_profile.profile_url = user_data.get('profile_url', existing_profile.profile_url)
            existing_profile.age = user_data.get('age', existing_profile.age)
            existing_profile.sex = user_data.get('sex', existing_profile.sex)
            existing_profile.city = user_data.get('city', existing_profile.city)
            saved_profiles.append(existing_profile)
        else:
            # Создаем новый профиль
            profile = create_or_update_profile(
                db=db,
                vk_id=user_data['vk_id'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                profile_url=user_data.get('profile_url'),
                age=user_data.get('age'),
                sex=user_data.get('sex'),
                city=user_data.get('city')
            )
            saved_profiles.append(profile)

    db.commit()
    return saved_profiles


def get_next_search_profile(db: Session, bot_user_id: int) -> Optional[Profile]:
    bot_user = get_bot_user_by_vk_id(db, bot_user_id)
    if not bot_user:
        return None

    # Базовый запрос
    query = db.query(Profile)

    # Добавляем фильтры по настройкам поиска
    prefs = get_search_preferences(db, bot_user.id)
    if prefs:
        if prefs.search_city:
            query = query.filter(Profile.city == prefs.search_city)
        if prefs.search_age_min:
            query = query.filter(Profile.age >= prefs.search_age_min)
        if prefs.search_age_max:
            query = query.filter(Profile.age <= prefs.search_age_max)
        if prefs.search_sex and prefs.search_sex != 0:
            query = query.filter(Profile.sex == prefs.search_sex)

    # Исключаем избранное
    fav_subq = db.query(Favorite.profile_id).filter(
        Favorite.bot_user_id == bot_user.id
    ).scalar_subquery()
    query = query.filter(~Profile.id.in_(fav_subq))

    # Исключаем черный список
    black_subq = db.query(Blacklist.profile_id).filter(
        Blacklist.bot_user_id == bot_user.id
    ).scalar_subquery()
    query = query.filter(Profile.id.notin_(black_subq))

    # Исключаем просмотренные
    viewed_subq = db.query(ViewedProfiles.profile_id).filter(
        ViewedProfiles.bot_user_id == bot_user.id
    ).scalar_subquery()
    query = query.filter(Profile.id.notin_(viewed_subq))

    # Берем случайный профиль
    count = query.count()
    if count == 0:
        return None
    return query.offset(random.randint(0, count - 1)).first()


def add_to_viewed_profiles(db: Session, bot_user_id: int, profile_id: int):
    # Добавляем профиль в просмотренные
    from src.database.models import ViewedProfiles
    # Проверяем, не добавлен ли уже
    existing = db.query(ViewedProfiles).filter(
        ViewedProfiles.bot_user_id == bot_user_id,
        ViewedProfiles.profile_id == profile_id
    ).first()

    if existing:
        return existing

    viewed = ViewedProfiles(
        bot_user_id=bot_user_id,
        profile_id=profile_id
    )
    db.add(viewed)
    db.commit()
    db.refresh(viewed)
    return viewed


def is_viewed(db: Session, bot_user_id: int, profile_id: int) -> bool:
    # Проверяем, просмотрен ли профиль
    from src.database.models import ViewedProfiles
    return db.query(ViewedProfiles).filter(
        ViewedProfiles.bot_user_id == bot_user_id,
        ViewedProfiles.profile_id == profile_id
    ).first() is not None


def get_viewed_profiles(db: Session, bot_user_id: int) -> List[Profile]:
    # Получаем просмотренные профили
    from src.database.models import ViewedProfiles
    viewed = db.query(ViewedProfiles).filter(ViewedProfiles.bot_user_id == bot_user_id).all()
    return [entry.profile for entry in viewed]

# ==================== Операции с лайками фотографий ====================

def add_photo_like(db: Session, bot_user_id: int, profile_id: int, photo_url: str) -> PhotoLike:
    # Добавить лайк на фото
    like = PhotoLike(
        bot_user_id=bot_user_id,
        profile_id=profile_id,
        photo_url=photo_url
    )
    db.add(like)
    db.commit()
    db.refresh(like)
    return like


def remove_photo_like(db: Session, bot_user_id: int, photo_url: str) -> bool:
    # Удалить лайк с фото
    like = db.query(PhotoLike).filter(
        PhotoLike.bot_user_id == bot_user_id,
        PhotoLike.photo_url == photo_url
    ).first()

    if like:
        db.delete(like)
        db.commit()
        return True
    return False


def get_user_photo_likes(db: Session, bot_user_id: int) -> List[PhotoLike]:
    # Получить все лайки пользователя
    return db.query(PhotoLike).filter(
        PhotoLike.bot_user_id == bot_user_id
    ).all()


def is_photo_liked(db: Session, bot_user_id: int, photo_url: str) -> bool:
    # Проверить, лайкнуто ли фото
    return db.query(PhotoLike).filter(
        PhotoLike.bot_user_id == bot_user_id,
        PhotoLike.photo_url == photo_url
    ).first() is not None
