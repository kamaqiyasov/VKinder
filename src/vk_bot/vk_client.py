import logging
from typing import Dict, List, Optional
import vk_api


logger = logging.getLogger(__name__)

class VKClient:
    def __init__(self, vk_id: int, user_token: Optional[str] = None) -> None:
        self.token = user_token
        self.vk_id = vk_id
        self.vk = None
        if user_token:
            self.set_token(user_token)
        logger.info("Инициализирован VKClient")
    
    def set_token(self, user_token: str) -> bool:
        """Установить токен пользователя"""
        logger.info(f"Проверка токена (длина: {len(user_token) if user_token else 0})")
        if not user_token or len(user_token) < 50:
            logger.warning("Токен слишком короткий")
            return False
        
        try:
            test_vk = vk_api.VkApi(token=user_token)
            api = test_vk.get_api()
            
            # Простой запрос для проверки
            response = api.users.get(user_ids=1)
            
            if response and isinstance(response, list):
                self.token = user_token
                self.vk = api
                logger.info("Токен успешно установлен")
                return True
        except vk_api.exceptions.ApiError as e:
            logger.error(f"Ошибка API при проверке токена: {e}")
            return False
        
        return False
    
    def get_user_info(self) -> dict:
        """Получает информацию о пользователе ВК"""
        if not self.vk:
            return {}
        response = self.vk.users.get(user_ids=self.vk_id, fields="city,sex,bdate,photo_max_orig")
        if not response:
            return {}
            
        return self._parse_user_info(response[0])
    
    def search_users(self, **kwargs) -> List[Dict]:
        """Поиск пользователей"""
        
        params = kwargs.copy()        
        logger.info(f"Передаю в VK: {params}")
        
        # Добавляем photo_id в fields, если его там нет
        if 'fields' in params:
            fields = params['fields']
            if 'photo_id' not in fields:
                params['fields'] = fields + ',photo_id'
        else:
            params['fields'] = 'photo_id'
        
        if not self.vk:
            return []
        
        try:
            response = self.vk.users.search(**params)
            count = response.get('count', [])
            items = response.get('items', [])
            logger.info(f"VK нашел {count} пользователей, вернул {len(items)}")
            return response
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return []
    
    def get_popular_profile_photos(self, user_id: int, count: int = 3) -> List[Dict]:
        """Получает популярные фото профиля по лайкам"""
        if not self.vk:
            return []
        
        try:
            response = self.vk.photos.get(
                owner_id=user_id,
                album_id='profile',
                count=100,
                extended=1,
                photo_sizes=1
            )
            
            items = response.get('items', [])
            if not items:
                return []
            
            sorted_photos = sorted(
                items, 
                key=lambda x: x.get('likes', {}).get('count', 0), 
                reverse=True
            )
            
            return sorted_photos[:count]
            
        except Exception as e:
            logger.error(f"Ошибка получения популярных фото {user_id}: {e}")
            return []
    
    def _parse_user_info(self, user_data: dict) -> dict:
        """Парсит данные пользователя из VK API"""
        info = {
            'first_name': user_data.get('first_name'),
            'last_name': user_data.get('last_name'),
            'vk_id': user_data.get('id')
        }
        
        bdate = user_data.get('bdate')
        if bdate and len(bdate.split('.')) == 3:
            from datetime import datetime
            birth_year = int(bdate.split('.')[2])
            age = datetime.now().year - birth_year
            info['age'] = age
        
        sex = user_data.get('sex')
        if sex in [1, 2]:
            info['sex'] = sex
        
        city = user_data.get('city')
        if city:
            info['city'] = city.get('title')
        
        return info
    
    def is_authenticated(self) -> bool:
        """Проверка, есть ли токен"""
        return self.vk is not None