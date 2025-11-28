
from typing import Optional, Dict, Any
from src.database.base import Session
from src.database.crud import get_user_state, create_or_update_user_state, update_user_state_data

class StateManager:
    def __init__(self) -> None:
        pass

    def set_state(self, vk_id: int, state: str):
        # Установка состояния пользователя
        with Session() as session:
            create_or_update_user_state(session, vk_id, state)

    def get_state(self, vk_id: int) -> Optional[str]:
        # Получение состояния пользователя
        with Session() as session:
            user_state = get_user_state(session, vk_id)
            return user_state.current_state if user_state else None

    def set_data(self, vk_id: int, **kwargs):
        # Установка данных состояния
        with Session() as session:
            user_state = get_user_state(session, vk_id)
            current_data = user_state.state_data if user_state else {}
            current_data.update(kwargs)
            state = user_state.current_state if user_state else 'start'
            create_or_update_user_state(session, vk_id, state, current_data)

    def get_data(self, vk_id: int, key: str = None) -> Any:
        # Получение данных состояния
        with Session() as session:
            user_state = get_user_state(session, vk_id)
            if user_state and user_state.state_data:
                return user_state.state_data.get(key) if key else user_state.state_data
            return None if key else {}

    def update_data(self, vk_id: int, **kwargs) -> Dict:
        # Обновление данных состояния
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

    def clear_state(self, vk_id: int):
        # Очистка состояния пользователя
        with Session() as session:
            from src.database.crud import delete_user_state
            delete_user_state(session, vk_id)