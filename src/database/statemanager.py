import logging

from typing import Optional
from src.database.base import Session
from src.database.models import UserState


logger = logging.getLogger(__name__)


class StateManager:
    def __init__(self) -> None:
        pass
    
    def set_state(self, user_id: int, state: str):
        with Session() as session:
            user_state = session.get(UserState, user_id)
            if user_state:
                logger.info(f"Обновляем состояние пользователя {user_id}: {user_state.state} → {state}")
                user_state.state = state
            else:
                logger.info(f"Создаём состояние пользователя {user_id}: {state}")
                user_state = UserState(user_id=user_id, state=state)
            session.add(user_state)
            session.commit()
                
    def get_state(self, user_id: int) -> Optional[str]:
        with Session() as session:
            user_state = session.get(UserState, user_id)
            state = user_state.state if user_state else None
            logger.debug(f"Получаем состояние пользователя {user_id}: {state}")
            return state
        
    def set_data(self, user_id: int, **kwargs):
        with Session() as session:
            user_state = session.get(UserState, user_id)
            if user_state:
                data = user_state.get_data()
                data.update(kwargs)
                user_state.set_data(data)
                logger.info(f"Обновляем данные пользователя {user_id}: {kwargs}")
            else:
                user_state = UserState(user_id=user_id)
                user_state.set_data(kwargs)
                session.add(user_state)
                logger.info(f"Создаём данные пользователя {user_id}: {kwargs}")
            session.commit()
            
    def get_data(self, user_id: int, key = None):
        with Session() as session:
            user_state = session.get(UserState, user_id)
            if user_state:
                data = user_state.get_data()
                res = data.get(key) if key else data
                logger.debug(f"Получаем данные пользователя {user_id}: {res}")
                return res
            return None if key else {}
    
    def update_data(self, user_id: int, **kwargs) -> dict:
        with Session() as session:
            user_state = session.get(UserState, user_id)
            if user_state:
                current_data = user_state.get_data()
                current_data.update(kwargs)
                user_state.set_data(current_data)
                session.commit()
                logger.info(f"Обновляем данные пользователя {user_id}: {kwargs}")
                return current_data
            else:
                user_state = UserState(user_id=user_id)
                user_state.set_data(kwargs)
                session.add(user_state)
                session.commit()
                logger.info(f"Создаём данные пользователя {user_id}: {kwargs}")
                return kwargs
    
    def clear_state(self, user_id: int):
        with Session() as session:
            user_state = session.get(UserState, user_id)
            if user_state:
                logger.info(f"Удаляем состояние пользователя {user_id}: {user_state.state}")
                session.delete(user_state)
                session.commit()