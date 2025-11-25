def state_handler(state_name):
    def decorator(func):
        func.state_name = state_name
        return func
    return decorator

class StateManager:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.state_handlers = {}
        self._collect_state_handlers()
        
    def _collect_state_handlers(self):
        for method_name in dir(self.bot):
            method = getattr(self.bot, method_name)
            if hasattr(method, 'state_name'):
                self.state_handlers[method.state_name] = method
    
    def handle_state(self, user_id: int, text: str):
        current_state = self.bot.user_states.get(user_id, "start")
        if current_state in self.state_handlers:
            self.state_handlers[current_state](user_id, text)
        else:
            self.bot.send_msg(user_id, "Неизвестное состояние")