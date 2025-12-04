import requests
import random
import time
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class VKSearcher:
    def __init__(self, access_token, version='5.131'):
        self.token = access_token
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}

    def _make_request(self, method, params):
        # Безопасный запрос к VK API
        url = f'https://api.vk.com/method/{method}'

        # Создаем копию параметров для логирования (скрываем токен)
        params_for_log = params.copy()
        if 'access_token' in params_for_log:
            params_for_log['access_token'] = '***HIDDEN***'

        logger.info(f"Отправка запроса к {method}")
        logger.info(f"URL: {url}")
        logger.info(f"Параметры (без токена): {params_for_log}")

        try:
            response = requests.get(url, params={**self.params, **params}, timeout=10)
            logger.info(f"Статус ответа: {response.status_code}")

            response.raise_for_status()
            data = response.json()

            logger.info(f"Полный ответ от VK API: {data}")

            if 'error' in data:
                error_code = data['error'].get('error_code')
                error_msg = data['error'].get('error_msg')
                logger.error(f"VK API Error {error_code}: {error_msg}")

                # Если слишком много запросов - ждем
                if error_code == 6:
                    time.sleep(0.5)
                    return self._make_request(method, params)

                # Если токен недействителен
                if error_code in [5, 28]:
                    logger.error("Токен недействителен или просрочен!")

                return None

            logger.info(f"Запрос успешен, получен ответ от {method}")
            return data.get('response')

        except requests.exceptions.Timeout:
            logger.error(f"Таймаут запроса к {method}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка сети при запросе к {method}: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка в запросе к {method}: {e}")
            return None

    def _get_city_id(self, city_name: str) -> Optional[int]:
        # Получение ID города по названию
        if not city_name:
            return None

        # Сначала попробуем найти в России
        city_data = self._make_request('database.getCities', {
            'country_id': 1,  # Россия
            'q': city_name,
            'count': 1
        })

        if city_data and city_data.get('items'):
            return city_data['items'][0]['id']

        # Если не нашли в России, ищем в других странах
        city_data = self._make_request('database.getCities', {
            'q': city_name,
            'count': 1
        })

        if city_data and city_data.get('items'):
            return city_data['items'][0]['id']

        logger.warning(f"Город '{city_name}' не найден в базе VK")
        return None


    def search_users(self, city: str, age_from: int, age_to: int,
                     sex: int = 0, offset: int = 0, count: int = 10) -> List[Dict]:
        # Поиск пользователей
        logger.info(f"=== НАЧАЛО ПОИСКА ===")
        logger.info(f"Запрос: город='{city}', возраст={age_from}-{age_to}, пол={sex}, offset={offset}, count={count}")

        # Получаем ID города
        city_id = None
        if city and city.strip():
            logger.info(f"Получаем ID города '{city}'...")
            try:
                city_id = self._get_city_id(city.strip())
                logger.info(f"ID города '{city}': {city_id}")
            except Exception as e:
                logger.error(f"Ошибка получения ID города: {e}")
                city_id = None

        # Параметры запроса
        params = {
            'sort': 0,  # По популярности
            'has_photo': 1,
            'count': min(count, 100),  # Максимум 100 за запрос
            'fields': 'photo_max_orig,sex,bdate,city,domain,can_write_private_message',
            'age_from': age_from,
            'age_to': age_to,
            'status': 6,  # В активном поиске
            'online': 0,  # Не только онлайн
            'offset': offset  # Используем переданный offset
        }

        if city_id:
            params['city'] = city_id
        elif city and city.strip():
            params['hometown'] = city.strip()

        if sex in [1, 2]:
            params['sex'] = sex
        elif sex == 0:
            pass

        logger.info(f"Параметры запроса к VK API: {params}")

        response = self._make_request('users.search', params)

        if not response:
            logger.warning("Пустой ответ от VK API")
            return []

        items = response.get('items', [])
        total_count = response.get('count', 0)

        logger.info(f"Всего найдено по запросу: {total_count} пользователей")
        logger.info(f"VK API вернул {len(items)} пользователей до фильтрации")

        users = []

        for i, user in enumerate(items):
            # Менее строгая фильтрация
            if user.get('is_closed', False):
                logger.debug(f"Пользователь {i}: закрытый профиль, пропускаем")
                continue

            # Рассчитываем возраст
            age = None
            bdate = user.get('bdate')
            if bdate and len(bdate.split('.')) >= 2:
                try:
                    bdate_parts = bdate.split('.')
                    if len(bdate_parts) == 3:  # Полная дата
                        bdate_obj = datetime.strptime(bdate, "%d.%m.%Y")
                        now = datetime.now()
                        age = now.year - bdate_obj.year
                        if (now.month, now.day) < (bdate_obj.month, bdate_obj.day):
                            age -= 1
                    elif len(bdate_parts) == 2:  # Только день и месяц
                        # Показываем, но возраст не указываем
                        age = None
                except Exception as e:
                    logger.debug(f"Ошибка парсинга даты рождения: {e}")

            # Определяем пол
            sex_int = user.get('sex', 0)

            # Получаем город
            city_name = None
            if 'city' in user:
                city_name = user['city'].get('title')
            elif city:
                city_name = city

            # Ссылка на профиль
            domain = user.get('domain', f"id{user['id']}")
            profile_url = f"https://vk.com/{domain}"

            users.append({
                'vk_id': user['id'],
                'first_name': user.get('first_name', ''),
                'last_name': user.get('last_name', ''),
                'profile_url': profile_url,
                'age': age,
                'sex': sex_int,
                'city': city_name,
                'photo_url': user.get('photo_max_orig')
            })

            logger.debug(f"Добавлен пользователь {i}: {user.get('first_name')} {user.get('last_name')}")

        logger.info(f"Найдено {len(users)} пользователей после фильтрации")
        logger.info(f"=== КОНЕЦ ПОИСКА ===")

        return users

    def get_user_photos(self, user_id: int) -> List[Dict]:
        # Получаем фото пользователя
        params = {
            'owner_id': user_id,
            'album_id': 'profile',
            'extended': 1,
            'count': 30,
            'photo_sizes': 1
        }

        response = self._make_request('photos.get', params)

        if not response:
            logger.warning(f"Не удалось получить фото пользователя {user_id}")
            return []

        items = response.get('items', [])

        if not items:
            return []

        # Сортируем по лайкам
        sorted_photos = sorted(
            items,
            key=lambda x: x.get('likes', {}).get('count', 0),
            reverse=True
        )

        top_photos = []
        for photo in sorted_photos[:3]:  # Берем топ-3 фото
            sizes = photo.get('sizes', [])

            if not sizes:
                continue  # Пропускаем фото без размеров

            # Ищем фото максимального размера
            size_types = ['w', 'z', 'y', 'x', 'm', 's']
            selected_size = None

            # Ищем первый подходящий размер
            for size_type in size_types:
                for size in sizes:
                    if size.get('type') == size_type:
                        selected_size = size
                        break
                if selected_size:
                    break

            # Если не нашли подходящий размер, берем первый доступный
            if not selected_size and sizes:
                selected_size = sizes[0]

            if selected_size:
                top_photos.append({
                    'url': selected_size['url'],
                    'likes': photo.get('likes', {}).get('count', 0),
                    'owner_id': photo.get('owner_id'),
                    'id': photo.get('id')
                })

        logger.info(f"Получено {len(top_photos)} фото для пользователя {user_id}")
        return top_photos

    def search_users_with_pagination(self, city: str, age_from: int, age_to: int,
                                     sex: int = 0, total_count: int = 1000) -> List[Dict]:
        # Поиск пользователей с пагинацией для обхода ограничений в 1000 результатов
        all_users = []
        max_offset = 1000  # VK ограничение
        batch_size = 100   # Максимум за запрос

        for offset in range(0, min(total_count, max_offset), batch_size):
            logger.info(f"Запрос пагинации: offset={offset}")

            users = self.search_users(
                city=city,
                age_from=age_from,
                age_to=age_to,
                sex=sex,
                offset=offset,
                count=batch_size
            )

            if not users:
                break

            all_users.extend(users)

            # Пауза между запросами чтобы избежать лимитов
            time.sleep(0.1)

        return all_users
