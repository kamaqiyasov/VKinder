from typing import Optional
from src.database.base import Session
from src.database.models import UserState


class StateManager:
    def __init__(self) -> None:
        pass
    
    def set_state(self, user_id: int, state: str):
        with Session() as session:
            user_state = session.get(UserState, user_id)
            if user_state:
                user_state.state = state
            else:
                user_state = UserState(user_id=user_id, state=state)
                session.add(user_state)
                session.commit()
                
    def get_state(self, user_id: int) -> Optional[str]:
        with Session() as session:
            user_state = session.get(UserState, user_id)
            return user_state.state if user_state else None
        
    def set_data(self, user_id: int, **kwargs):
        with Session() as session:
            user_state = session.get(UserState, user_id)
            if user_state:
                data = user_state.get_data()
                data.update(kwargs)
                user_state.set_data(data)
            else:
                user_state = UserState(user_id=user_id)
                user_state.set_data(kwargs)
                session.add(user_state)
            session.commit()
            
    def get_data(self, user_id: int, key = None):
        with Session() as session:
            user_state = session.get(UserState, user_id)
            if user_state:
                data = user_state.get_data()
                return data.get(key) if key else data
            return None if key else {}
    
    def update_data(self, user_id: int, **kwargs) -> dict:
        with Session() as session:
            user_state = session.get(UserState, user_id)
            if user_state:
                current_data = user_state.get_data()
                current_data.update(kwargs)
                user_state.set_data(current_data)
                session.commit()
                return current_data
            else:
                user_state = UserState(user_id=user_id)
                user_state.set_data(kwargs)
                session.add(user_state)
                session.commit()
                return kwargs
    
    def clear_state(self, user_id: int):
        with Session() as session:
            user_state = session.get(UserState, user_id)
            if user_state:
                session.delete(user_state)
                session.commit()