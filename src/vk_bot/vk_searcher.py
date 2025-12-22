import requests
import time
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class VKAPIError(Exception):
    """Кастомное исключение для ошибок VK API"""


class RateLimiter:
    """Ограничитель запросов к VK API"""

    def __init__(self, max_requests_per_second: float = 2.0):
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0
        self.request_count = 0
        self.reset_time = time.time()

    def wait_if_needed(self):
        """Ожидание при необходимости"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()


class VKSearcher:
    """Класс для поиска пользователей ВКонтакте"""

    API_URL = "https://api.vk.com/method/"
    API_VERSION = "5.131"

    def __init__(self, access_token: str):
        self.token = access_token
        self.rate_limiter = RateLimiter()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'VKinder/1.0'
        })

    def _make_request(self, method: str, params: Dict) -> Optional[Dict]:
        """Выполнение запроса к VK API"""
        self.rate_limiter.wait_if_needed()

        url = f"{self.API_URL}{method}"
        params.update({
            'access_token': self.token,
            'v': self.API_VERSION
        })

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'error' in data:
                error = data['error']
                logger.error(f"VK API Error {error.get('error_code')}: "
                             f"{error.get('error_msg')}")
                self._handle_api_error(error)
                return None

            return data.get('response')

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка сети при запросе к {method}: {e}")
            return None
        except requests.exceptions.Timeout:
            logger.error("Таймаут запроса к VK API")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Ошибка соединения с VK API")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при запросе к {method}: {e}")
            return None

    def _handle_api_error(self, error: Dict):
        """Обработка ошибок VK API"""
        error_code = error.get('error_code')

        if error_code == 6:  # Too many requests
            time.sleep(0.5)
        elif error_code == 29:  # Rate limit
            time.sleep(1)
        elif error_code in [5, 28]:  # Invalid token
            raise VKAPIError("Токен недействителен или просрочен")

    def search_users(self, city: str, age_from: int, age_to: int,
                     sex: int = 0, offset: int = 0, count: int = 1000,
                     sort: int = 0, hometown: str = None) -> List[Dict]:
        """Упрощенный поиск пользователей"""
        logger.info(f"Поиск: город='{city}', возраст={age_from}-{age_to}, пол={sex}, offset={offset}, sort={sort}")

        # Получаем ID города
        city_id = None
        if city and city.strip():
            city_id = self._get_city_id(city.strip())
            logger.info(f"ID города '{city}': {city_id}")

        # Базовые параметры запроса
        params = {
            'sort': sort,  # 0 - по популярности, 1 - по дате регистрации
            'has_photo': 1,
            'count': min(count, 1000),
            'fields': 'photo_max_orig,sex,bdate,city,domain',
            'age_from': age_from,
            'age_to': age_to,
            'offset': offset
        }

        # Добавляем параметры в зависимости от наличия
        if city_id:
            params['city'] = city_id
        elif city and city.strip():
            params['hometown'] = city.strip()

        # Если указан родной город отдельно
        if hometown and hometown.strip():
            params['hometown'] = hometown.strip()

        if sex in [1, 2]:
            params['sex'] = sex

        logger.debug(f"Параметры запроса: {params}")

        response = self._make_request('users.search', params)

        if not response:
            logger.warning("Пустой ответ от API")
            return []

        items = response.get('items', [])
        total_count = response.get('count', 0)

        logger.info(f"Всего найдено: {total_count}, возвращено: {len(items)}")

        return self._parse_users_response(items)

    def _get_city_id(self, city_name: str) -> Optional[int]:
        """Получение ID города"""
        if not city_name:
            return None

        city_data = self._make_request('database.getCities', {
            'q': city_name,
            'count': 1
        })

        if city_data and city_data.get('items'):
            return city_data['items'][0]['id']

        logger.warning(f"Город '{city_name}' не найден")
        return None

    def _parse_users_response(self, users: List[Dict]) -> List[Dict]:
        """Парсинг ответа с пользователями"""
        parsed_users = []

        for user in users:
            if user.get('is_closed', False):
                continue

            parsed_user = {
                'vk_id': user['id'],
                'first_name': user.get('first_name', ''),
                'last_name': user.get('last_name', ''),
                'profile_url': self._get_profile_url(user),
                'age': self._calculate_age(user.get('bdate')),
                'sex': user.get('sex', 0),
                'city': user.get('city', {}).get('title') if user.get('city') else None,
                'photo_url': user.get('photo_max_orig')
            }

            parsed_users.append(parsed_user)

        return parsed_users

    def _get_profile_url(self, user: Dict) -> str:
        """Получение URL профиля"""
        domain = user.get('domain', f"id{user['id']}")
        return f"https://vk.com/{domain}"

    def _calculate_age(self, bdate: Optional[str]) -> Optional[int]:
        """Расчет возраста по дате рождения"""
        if not bdate:
            return None

        try:
            parts = bdate.split('.')
            if len(parts) != 3:
                return None

            day, month, year = map(int, parts)
            birth_date = datetime(year, month, day)
            today = datetime.now()

            age = today.year - birth_date.year
            if (today.month, today.day) < (birth_date.month, birth_date.day):
                age -= 1

            return age
        except (ValueError, AttributeError):
            return None

    def get_user_tagged_photos(self, user_id: int) -> List[Dict]:
        """Получение фотографий, где отмечен пользователь"""
        params = {
            'user_id': user_id,
            'count': 30,
            'extended': 1
        }

        response = self._make_request('photos.getUserPhotos', params)

        if not response:
            return []

        items = response.get('items', [])

        # Сортируем по лайкам и берем топ-3
        sorted_photos = sorted(
            items,
            key=lambda x: x.get('likes', {}).get('count', 0),
            reverse=True
        )[:3]

        photos = []
        for photo in sorted_photos:
            sizes = photo.get('sizes', [])
            if sizes:
                # Берем фото максимального размера
                size_types = ['w', 'z', 'y', 'x', 'm', 's']
                selected_size = None

                for size_type in size_types:
                    for size in sizes:
                        if size.get('type') == size_type:
                            selected_size = size
                            break
                    if selected_size:
                        break

                if selected_size:
                    photos.append({
                        'url': selected_size['url'],
                        'likes': photo.get('likes', {}).get('count', 0),
                        'owner_id': photo.get('owner_id'),
                        'id': photo.get('id')
                    })

        return photos

    def smart_search_users(self, city: str, age_from: int, age_to: int,
                           sex: int = 0, target_count: int = 1500) -> List[Dict]:
        """Умный поиск с обходом ограничений VK API"""
        try:
            if city is None and sex == 0:
                logger.warning("Мало параметров для поиска, будут использованы широкие критерии")

            MAX_REQUESTS = 10  # Ограничение VK API
            all_users = []
            requests_made = 0

            # Стратегии поиска с ограничением по количеству запросов
            strategies = [
                {"sort": 0, "offset_range": range(0, 1000, 100)},  # по популярности
                {"sort": 1, "offset_range": range(0, 500, 100)},   # по дате регистрации
            ]

            for strategy in strategies:
                if len(all_users) >= target_count or requests_made >= MAX_REQUESTS:
                    break

                for offset in strategy["offset_range"]:
                    if len(all_users) >= target_count or requests_made >= MAX_REQUESTS:
                        break

                    users = self.search_users(
                        city=city,
                        age_from=age_from,
                        age_to=age_to,
                        sex=sex,
                        offset=offset,
                        sort=strategy["sort"]
                    )
                    requests_made += 1

                    if users:
                        existing_ids = {u['vk_id'] for u in all_users}
                        new_users = [u for u in users if u['vk_id'] not in existing_ids]
                        all_users.extend(new_users)

            return all_users[:target_count]
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
        return []

    def get_user_photos(self, user_id: int, include_tagged: bool = False) -> List[Dict]:
        """Получение фотографий пользователя (профиль + отмеченные)"""
        profile_photos = self.get_user_profile_photos(user_id)

        if include_tagged:
            tagged_photos = self.get_user_tagged_photos(user_id)
            # Объединяем и сортируем по лайкам
            all_photos = profile_photos + tagged_photos
            all_photos.sort(key=lambda x: x.get('likes', 0), reverse=True)
            return all_photos[:6]  # Возвращаем до 6 фото

        return profile_photos


    def get_user_profile_photos(self, user_id: int) -> List[Dict]:
        """Получение только фотографий профиля"""
        params = {
            'owner_id': user_id,
            'album_id': 'profile',
            'extended': 1,
            'count': 30
        }

        response = self._make_request('photos.get', params)

        if not response:
            return []

        items = response.get('items', [])

        # Сортируем по лайкам и берем топ-3
        sorted_photos = sorted(
            items,
            key=lambda x: x.get('likes', {}).get('count', 0),
            reverse=True
        )[:3]

        photos = []
        for photo in sorted_photos:
            sizes = photo.get('sizes', [])
            if sizes:
                # Берем фото максимального размера
                size_types = ['w', 'z', 'y', 'x', 'm', 's']
                selected_size = None

                for size_type in size_types:
                    for size in sizes:
                        if size.get('type') == size_type:
                            selected_size = size
                            break
                    if selected_size:
                        break

                if selected_size:
                    photos.append({
                        'url': selected_size['url'],
                        'likes': photo.get('likes', {}).get('count', 0),
                        'owner_id': photo.get('owner_id'),
                        'id': photo.get('id')
                    })

        return photos

    def search_by_interests(self, city: str, interests: List[str], age_from: int = 18,
                            age_to: int = 45, sex: int = 0, limit: int = 100) -> List[Dict]:
        """Поиск пользователей по интересам через группы"""

        found_users = []

        for interest in interests[:3]:  # Ограничиваем 3 интересами
            # Ищем группы по интересу
            groups = self._make_request('groups.search', {
                'q': interest,
                'count': 20,
                'sort': 6  # по количеству участников
            })

            if not groups or not groups.get('items'):
                continue

            group_ids = [group['id'] for group in groups['items'][:5]]  # Берем топ-5 групп

            for group_id in group_ids:
                # Получаем участников группы
                members = self._make_request('groups.getMembers', {
                    'group_id': group_id,
                    'count': 100,
                    'fields': 'sex,bdate,city'
                })

                if not members:
                    continue

                # Фильтруем по параметрам
                for user in members.get('items', []):
                    if user.get('is_closed', False):
                        continue

                    # Проверяем возраст
                    age = self._calculate_age(user.get('bdate'))
                    if not (age_from <= age <= age_to):
                        continue

                    # Проверяем пол
                    if sex != 0 and user.get('sex', 0) != sex:
                        continue

                    # Проверяем город
                    user_city = user.get('city', {}).get('title') if user.get('city') else None
                    if city and user_city and user_city.lower() != city.lower():
                        continue

                    # Добавляем пользователя
                    parsed_user = {
                        'vk_id': user['id'],
                        'first_name': user.get('first_name', ''),
                        'last_name': user.get('last_name', ''),
                        'profile_url': self._get_profile_url(user),
                        'age': age,
                        'sex': user.get('sex', 0),
                        'city': user_city,
                        'interests': [interest]
                    }

                    # Проверяем дубликаты
                    if not any(u['vk_id'] == parsed_user['vk_id'] for u in found_users):
                        found_users.append(parsed_user)

                    if len(found_users) >= limit:
                        return found_users

        return found_users
