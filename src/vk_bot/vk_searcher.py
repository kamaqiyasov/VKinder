import requests
import random
from typing import List, Dict, Optional
from datetime import datetime


class VKSearcher:
    def __init__(self, access_token, version='5.131'):
        self.token = access_token
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}

    def search_users(self, city: str, age_from: int, age_to: int,
                     sex: int = 0, offset: int = 0, count: int = 10) -> List[Dict]:
        """
        Поиск пользователей VK по критериям
        sex: 1 - женский, 2 - мужской, 0 - любой
        """
        url = 'https://api.vk.com/method/users.search'

        # Используем случайный offset для разнообразия
        if offset == 0:
            offset = random.randint(0, 900)  # VK ограничивает 1000 результатов

        params = {
            'city': city,
            'age_from': age_from,
            'age_to': age_to,
            'sex': sex,
            'offset': offset,
            'count': count,
            'fields': 'photo_max_orig,sex,bdate,city,photo_id',
            'has_photo': 1,
            'status': 1,  # Не женат/не замужем
            'sort': 0  # По популярности
        }

        try:
            response = requests.get(url, params={**self.params, **params})
            response.raise_for_status()
            data = response.json()

            if 'error' in data:
                print(f"VK API Error: {data['error']}")
                return []

            users = []
            items = data.get('response', {}).get('items', [])

            for user in items:
                # Пропускаем закрытые профили
                if user.get('is_closed', True):
                    continue

                # Рассчитываем возраст из даты рождения
                age = None
                if 'bdate' in user and len(user['bdate'].split('.')) == 3:
                    try:
                        bdate = datetime.strptime(user['bdate'], "%d.%m.%Y")
                        age = datetime.now().year - bdate.year
                        if datetime.now().month < bdate.month or \
                                (datetime.now().month == bdate.month and datetime.now().day < bdate.day):
                            age -= 1
                    except:
                        pass

                # Определяем пол
                sex_str = None
                if user.get('sex') == 1:
                    sex_str = 'Женский'
                elif user.get('sex') == 2:
                    sex_str = 'Мужской'

                # Получаем город
                city_name = None
                if 'city' in user:
                    city_name = user['city'].get('title')

                users.append({
                    'vk_id': user['id'],
                    'first_name': user.get('first_name', ''),
                    'last_name': user.get('last_name', ''),
                    'photo_url': user.get('photo_max_orig'),
                    'profile_url': f"https://vk.com/id{user['id']}",
                    'age': age,
                    'sex': sex_str,
                    'city': city_name
                })

            return users

        except Exception as e:
            print(f"Ошибка поиска VK: {e}")
            return []

    def get_user_photos(self, user_id: int) -> List[Dict]:
        """Получение топ-3 фотографий пользователя по количеству лайков"""
        url = 'https://api.vk.com/method/photos.getAll'
        params = {
            'owner_id': user_id,
            'extended': 1,
            'count': 100,
            'no_service_albums': 1
        }

        try:
            response = requests.get(url, params={**self.params, **params})
            data = response.json()

            if 'error' in data:
                print(f"VK Photos Error: {data['error']}")
                return []

            photos = data.get('response', {}).get('items', [])

            # Сортируем по количеству лайков и берем топ-3
            sorted_photos = sorted(
                photos,
                key=lambda x: x.get('likes', {}).get('count', 0),
                reverse=True
            )

            top_photos = []
            for photo in sorted_photos[:3]:
                # Берем фото самого большого размера
                sizes = photo.get('sizes', [])
                if sizes:
                    # Последний размер обычно самый большой
                    largest_size = sizes[-1]
                    top_photos.append({
                        'url': largest_size['url'],
                        'likes': photo.get('likes', {}).get('count', 0)
                    })

            return top_photos

        except Exception as e:
            print(f"Ошибка получения фото: {e}")
            return []