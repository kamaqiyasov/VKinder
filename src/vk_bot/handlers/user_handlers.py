import logging
from typing import Optional, Dict, List, Tuple
from src.vk_bot.vk_client import VKClient
from src.database.crud import get_or_create_search_settings, get_user_by_vk_id, save_user_with_token

logger = logging.getLogger(__name__)

class UserHandlers:
    
    def __init__(self) -> None:
        self.user_states: dict[int, dict] = {}
        logger.info("Инициализирован UserHandlers")
        
    def get_token_instruction(self) -> str:
        return (
            "Чтобы получить токен:\n\n"
            "1. Перейди: https://vkhost.github.io\n"
            "2. Выбери 'VK Admin'\n"
            "3. Нажми 'Разрешить'\n"
            "4. Скопируй токен из адресной строки\n\n"
            "Пришли в формате: token=твой_токен"
        )
    
    def handle_token_input(self, vk_client: VKClient, user_id: int, token: str) -> Tuple[Optional[bool], Optional[str]]:
        """Обрабатывает ввод токена"""
        logger.info(f"Пользователь {user_id}: обработка токена")
        # Проверяем, есть ли такой пользователь в БД
        existing_user = get_user_by_vk_id(user_id)
        
        if existing_user and existing_user.access_token:
            return False, "У вас уже есть токен. Напиши 'Старт' для начала"
        
        success = vk_client.set_token(token)
        if not success:
            logger.warning(f"Пользователь {user_id}: неверный токен")
            return False, "Неверный токен"
        
        logger.info(f"Пользователь {user_id}: токен валиден")
        user_info = vk_client.get_user_info(user_id)
        missing = self._get_missing_fields(user_info)
        
        if not missing:
            db_success = save_user_with_token(user_id, token, user_info)
            if db_success:
                return True, "Данные сохранены"
            return False, "Ошибка сохранения в БД"
        
        self.user_states[user_id] = {
            'temp_token': token,
            'temp_user_info': user_info,
            'missing_fields': missing,
            'answers': {}
        }
        return None, missing[0][1]
    
    def handle_state_response(self, user_id: int, text: str) -> Tuple[Optional[bool], Optional[str]]:
        """Обрабатывает ответ в состоянии"""
        if user_id not in self.user_states:
            return None, None
        
        state_data = self.user_states[user_id]
        current_field, question = state_data['missing_fields'][0]
        
        is_valid, error_msg = self._validate_field(current_field, text)
        if not is_valid:
            return False, f"{error_msg}\n\n{question}"
        
        state_data['answers'][current_field] = text.strip()
        state_data['missing_fields'].pop(0)
        
        if state_data['missing_fields']:
            _, next_question = state_data['missing_fields'][0]
            return None, next_question
        
        success = self._save_complete_user_data(user_id, state_data)
        del self.user_states[user_id]
        return success, "Все данные сохранены" if success else "Ошибка сохранения"
    
    def has_active_state(self, user_id: int) -> bool:
        """Проверяет активное состояние"""
        return user_id in self.user_states
    
    def _get_missing_fields(self, user_info: Dict) -> List[Tuple[str, str]]:
        """Определяет недостающие поля"""
        missing = []
        if 'age' not in user_info:
            missing.append(('age', "Сколько тебе лет? (число)"))
        if 'sex' not in user_info:
            missing.append(('sex', "Укажи пол:\n1 - женский\n2 - мужской"))
        if 'city' not in user_info:
            missing.append(('city', "Из какого ты города?"))
        return missing
    
    def _save_complete_user_data(self, user_id: int, state_data: Dict) -> bool:
        """Сохраняет собранные данные"""
        user_info = state_data['temp_user_info'].copy()
        user_info.update(state_data['answers'])
        
        if 'age' in user_info:
            try:
                user_info['age'] = int(user_info['age'])
            except:
                user_info['age'] = None
        
        search_sex = None
        if 'sex' in user_info:
            if user_info['sex'] == 1:  # пользователь женщина
                search_sex = 2  # ищем мужчин
            elif user_info['sex'] == 2:  # пользователь мужчина
                search_sex = 1  # ищем женщин
        
        success = save_user_with_token(user_id, state_data['temp_token'], user_info)
        if not success:
            return False
        user = get_user_by_vk_id(user_id)
        if not user:
            return False
        
        get_or_create_search_settings(
            vk_user_id=user.id,
            age=user_info.get('age'),
            city=user_info.get('city'),
            sex=search_sex
        )
        
        return True
    
    def _validate_field(self, field: str, value: str) -> Tuple[bool, str]:
        """Валидация введенных данных"""
        value = value.strip()
        
        if field == 'age':
            if not value.isdigit():
                return False, "Возраст должен быть числом"
            age = int(value)
            if not (5 <= age <= 120):
                return False, "Возраст должен быть от 5 до 120 лет"
            return True, ""
        
        elif field == 'sex':
            if value not in ['1', '2']:
                return False, "Укажи 1 (женский) или 2 (мужской)"
            return True, ""
        
        elif field == 'city':
            if value.isdigit():
                return False, "Город не может быть числом"
            if len(value) < 2:
                return False, "Название города слишком короткое"
            return True, ""
        
        return True, ""