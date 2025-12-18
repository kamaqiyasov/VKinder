import logging
from typing import Optional, Dict, List, Tuple
from src.database.crud import get_or_create_search_settings, get_user_by_vk_id, save_user_with_token
from src.config import settings
from src.vk_bot.vk_client import VKClient

logger = logging.getLogger(__name__)

class UserHandlers:
    
    def __init__(self) -> None:
        self.user_states: dict[int, dict] = {}
        logger.info("Инициализирован UserHandlers")
    
    def check_token_exists(self, user_id: int) -> Optional[str]:
        """Проверяет есть ли токен в БД"""
        user = get_user_by_vk_id(user_id)
        if user:
            return user.access_token
    
    def get_auth_instruction(self, user_id: int) -> Tuple[str, str]:
        """
        Возвращает инструкцию и ссылку для авторизации
        Returns: (message, auth_url)
        """
        auth_url = (
            f"https://oauth.vk.com/authorize?"
            f"client_id=54388226&"
            f"display=page&"
            f"redirect_uri=https://oauth.vk.com/blank.html&"
            f"response_type=token&"
            f"scope=friends,photos&"
            f"state={user_id}&"
            f"v=5.199"
        )
        
        message = (
            "🔐 Для работы бота нужен доступ к твоему VK аккаунту\n\n"
            "📋 Инструкция:\n"
            "1. Нажми на ссылку ниже\n"
            "2. Разреши доступ приложению\n"
            "3. Токен автоматически сохранится в системе\n"
            "4. Вернись и нажми 'Проверить авторизацию'\n\n"
            "⚠️ Это безопасно — бот не получает твой пароль"
        )
        
        return message, auth_url
    
    def get_welcome_back_message(self, user_id: int) -> str:
        """Сообщение для уже авторизованного пользователя"""
        user = get_user_by_vk_id(user_id)
        if user:
            return f"👋 С возвращением, {user.first_name}! Ты уже авторизован."
        return "👋 С возвращением!"
    
    def handle_token_input(self, vk_client, user_id: int, token: str) -> Tuple[Optional[bool], str]:
        """Обработка ввода токена - проверка и сохранение"""
        vk_client = VKClient(user_id, token)
        # Проверяем токен через VK API
        user_info = vk_client.get_user_info()
        if not user_info:
            return False, "Неверный токен"
        
        return self._register_user(user_id, token, user_info)
    
    def _register_user(self, user_id: int, token: str, user_info: Dict) -> Tuple[Optional[bool], str]:
        """Регистрация пользователя с запросом недостающих данных"""
        # Проверяем какие данные есть
        missing = self._get_missing_fields(user_info)
                
        if not missing:
            # Все данные есть - сразу сохраняем
            success = self._save_user(user_id, token, user_info)
            return success, "Регистрация завершена" if success else "Ошибка сохранения"
        
        # Нужно запросить данные
        self.user_states[user_id] = {
            'token': token,
            'user_info': user_info,
            'missing_fields': missing,
            'answers': {}
        }

        _, first_question = missing[0]
        return False, first_question
    
    def handle_state_response(self, user_id: int, text: str) -> Tuple[Optional[bool], str]:
        """Обрабатывает ответ в состоянии сбора данных"""
        if user_id not in self.user_states:
            return None, "Нет активной регистрации"
        
        state = self.user_states[user_id]
        field, question = state['missing_fields'][0]
        
        # Валидация
        is_valid, error = self._validate_field(field, text)
        if not is_valid:
            return False, f"{error}\n\n{question}"
        
        # Сохраняем ответ
        state['answers'][field] = text
        state['missing_fields'].pop(0)
        
        if state['missing_fields']:
            # Следующий вопрос
            _, next_q = state['missing_fields'][0]
            return None, next_q
        
        # Все данные собраны - сохраняем
        user_info = {**state['user_info'], **state['answers']}
        success = self._save_user(user_id, state['token'], user_info)
        
        # Очищаем состояние
        del self.user_states[user_id]
        
        return success, "Регистрация завершена" if success else "Ошибка сохранения"
    
    def has_active_state(self, user_id: int) -> bool:
        """Проверяет активное состояние регистрации"""
        return user_id in self.user_states
    
    def _get_missing_fields(self, user_info: Dict) -> List[Tuple[str, str]]:
        """Определяет недостающие поля"""
        missing = []
        
        if not user_info.get('age'):
            missing.append(('age', "Сколько тебе лет?"))
        
        if not user_info.get('sex'):
            missing.append(('sex', "Твой пол? (1-жен, 2-муж)"))
        
        if not user_info.get('city'):
            missing.append(('city', "Из какого вы города?"))
        
        return missing
    
    def _validate_field(self, field: str, value: str) -> Tuple[bool, str]:
        """Простая валидация"""
        value = value.strip()
        
        if field == 'age':
            if not value.isdigit():
                return False, "Введи число"
            age = int(value)
            if age < 5 or age > 120:
                return False, "Возраст 5-120 лет"
            return True, ""
        
        elif field == 'sex':
            if value not in ['1', '2']:
                return False, "Введи 1 или 2"
            return True, ""
        
        elif field == 'city':
            if len(value) < 2:
                return False, "Слишком коротко"
            return True, ""
        
        return True, ""
    
    def _save_user(self, user_id: int, token: str, user_info: Dict) -> bool:
        """Сохраняет пользователя в БД"""
        # Определяем пол для поиска
        search_sex = None
        sex = user_info.get('sex')
        if sex == '1' or sex == 1:  # пользователь женщина
            search_sex = 2  # ищем мужчин
        elif sex == '2' or sex == 2:  # пользователь мужчина
            search_sex = 1  # ищем женщин
        
        # Сохраняем пользователя
        success = save_user_with_token(user_id, token, user_info)
        if not success:
            return False
        
        user = get_user_by_vk_id(user_id)
        if not user:
            return False
        
        # Создаем настройки поиска
        get_or_create_search_settings(
            vk_user_id=user.id,
            age=user_info.get('age'),
            city=user_info.get('city'),
            sex=search_sex
        )
        
        return True