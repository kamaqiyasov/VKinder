from typing import Optional, Dict, Any
from sqlalchemy.exc import SQLAlchemyError
import logging
from src.database.base import Session
from src.database.crud import get_user_state, create_or_update_user_state, delete_user_state

logger = logging.getLogger(__name__)

class StateManager:
    """Менеджер состояний пользователей"""

    def __init__(self) -> None:
        self.Session = Session

    def set_state(self, vk_id: int, state: str) -> bool:
        """Установка состояния пользователя"""
        try:
            with Session() as session:
                create_or_update_user_state(session, vk_id, state)
                return True
        except SQLAlchemyError as e:
            logger.error(f"Ошибка установки состояния для пользователя {vk_id}: {e}")
            return False

    def get_state(self, vk_id: int) -> Optional[str]:
        """Получение состояния пользователя"""
        try:
            with Session() as session:
                user_state = get_user_state(session, vk_id)
                return user_state.current_state if user_state else None
        except SQLAlchemyError as e:
            logger.error(f"Ошибка получения состояния пользователя {vk_id}: {e}")
            return None


    def update_data(self, vk_id: int, **kwargs) -> Dict:
        """Обновление данных состояния"""
        with Session() as session:
            user_state = get_user_state(session, vk_id)
            if user_state:
                current_data = user_state.state_data or {}
                current_data.update(kwargs)
                create_or_update_user_state(session, vk_id, user_state.current_state, current_data)
                return current_data
            else:
                create_or_update_user_state(session, vk_id, 'start', kwargs)
                return kwargs

    def set_data(self, vk_id: int, **kwargs) -> None:
        """Установка данных состояния (полная замена)"""
        with Session() as session:
            user_state = get_user_state(session, vk_id)
            current_state = user_state.current_state if user_state else 'start'

            data_to_save = kwargs.copy()
            if 'vk_id' in data_to_save:
                del data_to_save['vk_id']

            create_or_update_user_state(session, vk_id, current_state, data_to_save)

    def get_data(self, vk_id: int, key: str = None) -> Any:
        """Получение данных состояния"""
        with Session() as session:
            user_state = get_user_state(session, vk_id)
            if user_state and user_state.state_data:
                return user_state.state_data.get(key) if key else user_state.state_data
            return None if key else {}

    def clear_state(self, vk_id: int) -> None:
        """Очистка состояния пользователя"""
        with Session() as session:
            delete_user_state(session, vk_id)