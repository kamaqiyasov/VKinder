# src/vk_bot/handlers.py
import logging
from typing import Dict, Any
from src.database.crud import get_user_by_vk_id, save_user_from_vk
from src.vk_bot.vk_client import VKUser
from src.config import settings

logger = logging.getLogger(__name__)

class Handlers:
    def __init__(self, bot):
        self.bot = bot
        self.FIELD_NAMES_RU = bot.FIELD_NAMES_RU
    
    # ============ ОЖИДАНИЕ СТАРТА ============
    
    def handle_start(self, user_id: int, request: str):
        """Обработка состояния 'start' (ожидание команды Начать)"""
        if request.lower() == 'начать':
            # Сначала проверяем, есть ли пользователь в нашей БД
            existing_user = get_user_by_vk_id(user_id)
            
            if existing_user and existing_user.is_profile_complete():
                # Пользователь уже зарегистрирован и профиль полный
                self.bot.send_msg(
                    user_id,
                    f"С возвращением, {existing_user.first_name}! 😊\n"
                    "Что вы хотите сделать?",
                    state="main"
                )
                self.bot.state_manager.set_state(user_id, "main")
                return
            
            # Получаем данные из ВК профиля
            vk_user_api = VKUser(access_token=settings.VK_TOKEN, user_id=user_id)
            vk_data = vk_user_api.user_info()
            
            if not vk_data:
                self.bot.send_msg(
                    user_id,
                    "❌ Не удалось получить данные из вашего профиля ВК.\n"
                    "Пожалуйста, как вас зовут?",
                    state=None
                )
                self.bot.state_manager.set_state(user_id, "registration_first_name")
                return
            
            # Проверяем, какие данные есть в ВК профиле
            missing_fields = self._check_missing_fields(vk_data)
            
            if not missing_fields:
                # Все данные есть в ВК - сохраняем и идем в главное меню
                if self._save_user_from_vk_data(user_id, vk_data):
                    self.bot.send_msg(
                        user_id,
                        f"🎉 Регистрация завершена!\n"
                        f"Добро пожаловать, {vk_data['first_name']}!\n"
                        f"Что вы хотите сделать?",
                        state="main"
                    )
                    self.bot.state_manager.set_state(user_id, "main")
                else:
                    self.bot.send_msg(
                        user_id,
                        "❌ Не удалось сохранить данные. Давайте заполним профиль вручную.\n"
                        "Как вас зовут?",
                        state=None
                    )
                    self.bot.state_manager.set_state(user_id, "registration_first_name")
            else:
                # Сохраняем то, что есть из ВК
                self._save_partial_user_data(user_id, vk_data)
                
                # Запрашиваем недостающие данные
                first_missing = missing_fields[0]
                self._ask_for_field(user_id, first_missing, vk_data)
                
        else:
            # Пользователь написал что-то другое
            self.bot.send_msg(
                user_id,
                "👋 Привет! Для начала работы нажмите кнопку 'Начать'",
                state="start"
            )
    
    # ============ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ============
    
    def _check_missing_fields(self, vk_data: Dict[str, Any]) -> list:
        """Проверяет, каких полей не хватает в данных из ВК"""
        missing = []
        
        # Проверяем обязательные поля
        if not vk_data.get('first_name') or not vk_data['first_name'].strip():
            missing.append('first_name')
        
        if not vk_data.get('age') or vk_data['age'] < 14 or vk_data['age'] > 100:
            missing.append('age')
        
        if not vk_data.get('sex') or vk_data['sex'] not in ['Мужской', 'Женский']:
            missing.append('sex')
        
        if not vk_data.get('city') or not vk_data['city'].strip():
            missing.append('city')
        
        return missing
    
    def _save_user_from_vk_data(self, user_id: int, vk_data: Dict[str, Any]):
        """Сохраняет полные данные из ВК в БД"""
        # Преобразуем возраст в int
        age = int(vk_data['age']) if vk_data.get('age') else None
        
        # Проверяем все обязательные поля
        if not all([vk_data.get('first_name'), age, vk_data.get('sex'), vk_data.get('city')]):
            return False
        
        # Сохраняем в БД
        save_user_from_vk(
            vk_id=user_id,
            first_name=vk_data['first_name'],
            last_name=vk_data.get('last_name', ''),
            vk_link=f"https://vk.com/id{user_id}",
            age=age,
            sex=vk_data['sex'],  # строка 'Мужской' или 'Женский'
            city=vk_data['city']
        )
        return True
    
    def _save_partial_user_data(self, user_id: int, vk_data: Dict[str, Any]):
        """Сохраняет частичные данные из ВК во временное хранилище"""
        # Сохраняем то, что есть в StateManager для дальнейшего использования
        if vk_data.get('first_name'):
            self.bot.state_manager.set_data(user_id, vk_first_name=vk_data['first_name'])
        if vk_data.get('last_name'):
            self.bot.state_manager.set_data(user_id, vk_last_name=vk_data['last_name'])
        if vk_data.get('age') and 14 <= vk_data['age'] <= 100:
            self.bot.state_manager.set_data(user_id, vk_age=vk_data['age'])
        if vk_data.get('sex') in ['Мужской', 'Женский']:
            sex_num = 1 if vk_data['sex'] == 'Женский' else 2
            self.bot.state_manager.set_data(user_id, vk_sex=sex_num)
        if vk_data.get('city'):
            self.bot.state_manager.set_data(user_id, vk_city=vk_data['city'])
    
    def _ask_for_field(self, user_id: int, field: str, vk_data: Dict[str, Any]):
        """Запрашивает у пользователя недостающее поле"""
        field_questions = {
            'first_name': "👋 Как вас зовут?",
            'age': f"Сколько вам лет, {vk_data.get('first_name', '')}?" if vk_data.get('first_name') else "Сколько вам лет?",
            'sex': "Укажите ваш пол:\n1 - Мужской 👨\n2 - Женский 👩",
            'city': "Из какого вы города?"
        }
        
        question = field_questions.get(field, f"Введите {self.FIELD_NAMES_RU.get(field, field)}")
        
        self.bot.send_msg(user_id, question, state=None)
        self.bot.state_manager.set_state(user_id, f"registration_{field}")
    
    # ============ РЕГИСТРАЦИЯ (для недостающих полей) ============
    
    def handle_registration_first_name(self, user_id: int, request: str):
        """Получение имени (если его нет в ВК)"""
        if len(request.strip()) < 2:
            self.bot.send_msg(user_id, "Пожалуйста, введите ваше имя (минимум 2 буквы)", state=None)
            return
        
        name = request.strip()
        self.bot.state_manager.set_data(user_id, first_name=name)
        
        # Проверяем, есть ли другие недостающие поля
        vk_data = self._get_vk_data_from_storage(user_id)
        missing = self._check_missing_fields({**vk_data, 'first_name': name})
        
        if 'age' in missing:
            self._ask_for_field(user_id, 'age', {**vk_data, 'first_name': name})
            self.bot.state_manager.set_state(user_id, "registration_age")
        elif 'sex' in missing:
            self._ask_for_field(user_id, 'sex', {**vk_data, 'first_name': name})
            self.bot.state_manager.set_state(user_id, "registration_sex")
        elif 'city' in missing:
            self._ask_for_field(user_id, 'city', {**vk_data, 'first_name': name})
            self.bot.state_manager.set_state(user_id, "registration_city")
        else:
            # Все поля заполнены - завершаем регистрацию
            self._complete_registration(user_id)
    
    def handle_registration_age(self, user_id: int, request: str):
        """Получение возраста (если его нет в ВК)"""
        try:
            age = int(request.strip())
            if age < 14 or age > 100:
                raise ValueError
            
            self.bot.state_manager.set_data(user_id, age=age)
            
            # Проверяем следующие недостающие поля
            vk_data = self._get_vk_data_from_storage(user_id)
            user_data = self.bot.state_manager.get_data(user_id)
            current_data = {**vk_data, **user_data}
            missing = self._check_missing_fields(current_data)
            
            if 'sex' in missing:
                self._ask_for_field(user_id, 'sex', current_data)
                self.bot.state_manager.set_state(user_id, "registration_sex")
            elif 'city' in missing:
                self._ask_for_field(user_id, 'city', current_data)
                self.bot.state_manager.set_state(user_id, "registration_city")
            else:
                self._complete_registration(user_id)
                
        except ValueError:
            self.bot.send_msg(user_id, "Пожалуйста, введите корректный возраст (число от 14 до 100)", state=None)
    
    def handle_registration_sex(self, user_id: int, request: str):
        """Получение пола (если его нет в ВК)"""
        request_lower = request.strip().lower()
        sex_map = {
            "1": 2, "2": 1,  # 1-муж, 2-жен (в твоей модели)
            "мужской": 2, "женский": 1,
            "м": 2, "ж": 1
        }
        
        if request_lower in sex_map:
            sex_num = sex_map[request_lower]
            self.bot.state_manager.set_data(user_id, sex=sex_num)
            
            # Проверяем следующие недостающие поля
            vk_data = self._get_vk_data_from_storage(user_id)
            user_data = self.bot.state_manager.get_data(user_id)
            current_data = {**vk_data, **user_data}
            missing = self._check_missing_fields(current_data)
            
            if 'city' in missing:
                self._ask_for_field(user_id, 'city', current_data)
                self.bot.state_manager.set_state(user_id, "registration_city")
            else:
                self._complete_registration(user_id)
        else:
            self.bot.send_msg(user_id, "Пожалуйста, выберите:\n1 - Мужской 👨\n2 - Женский 👩", state=None)
    
    def handle_registration_city(self, user_id: int, request: str):
        """Получение города (если его нет в ВК)"""
        city = request.strip()
        if len(city) < 2:
            self.bot.send_msg(user_id, "Пожалуйста, введите название города", state=None)
            return
        
        self.bot.state_manager.set_data(user_id, city=city)
        self._complete_registration(user_id)
    
    def _get_vk_data_from_storage(self, user_id: int) -> Dict[str, Any]:
        """Получает данные из ВК из временного хранилища"""
        data = self.bot.state_manager.get_data(user_id)
        vk_data = {}
        
        # Извлекаем VK данные
        if data.get('vk_first_name'):
            vk_data['first_name'] = data['vk_first_name']
        if data.get('vk_last_name'):
            vk_data['last_name'] = data['vk_last_name']
        if data.get('vk_age'):
            vk_data['age'] = data['vk_age']
        if data.get('vk_sex'):
            vk_data['sex'] = 'Женский' if data['vk_sex'] == 1 else 'Мужский'
        if data.get('vk_city'):
            vk_data['city'] = data['vk_city']
        
        return vk_data
    
    def _complete_registration(self, user_id: int):
        """Завершает регистрацию, сохраняя все данные"""
        # Получаем все данные
        vk_data = self._get_vk_data_from_storage(user_id)
        user_data = self.bot.state_manager.get_data(user_id)
        
        # Объединяем данные (пользовательские данные имеют приоритет)
        clean_data = {}
        for key, value in user_data.items():
            if not key.startswith('vk_'):
                clean_data[key] = value
        
        # Подготавливаем данные для сохранения
        first_name = clean_data.get('first_name') or vk_data.get('first_name')
        last_name = vk_data.get('last_name', '')  # может быть None, делаем пустую строку
        
        # Возраст
        age_value = clean_data.get('age') or vk_data.get('age')
        age = int(age_value) if age_value is not None else None
        
        # Пол (преобразуем в строку 'Мужской'/'Женский')
        sex_num = clean_data.get('sex') or (1 if vk_data.get('sex') == 'Женский' else 2 if vk_data.get('sex') == 'Мужской' else None)
        sex_str = 'Женский' if sex_num == 1 else 'Мужской' if sex_num == 2 else ''
        
        # Город
        city = clean_data.get('city') or vk_data.get('city', '')
        
        # Проверяем, что все обязательные поля есть
        if not all([first_name, age is not None, sex_str, city]):
            missing = []
            if not first_name: missing.append('имя')
            if age is None: missing.append('возраст')
            if not sex_str: missing.append('пол')
            if not city: missing.append('город')
            
            self.bot.send_msg(
                user_id,
                f"❌ Не хватает данных: {', '.join(missing)}\n"
                "Пожалуйста, заполните все поля.",
                state=None
            )
            return
        
        # Сохраняем в БД
        save_user_from_vk(
            vk_id=user_id,
            first_name=first_name,
            last_name=last_name or '',  # гарантируем строку
            vk_link=f"https://vk.com/id{user_id}",
            age=age,
            sex=sex_str,  # строка 'Мужской' или 'Женский'
            city=city
        )
        
        self.bot.send_msg(
            user_id,
            f"🎉 Регистрация завершена!\n"
            f"Добро пожаловать, {first_name}!\n"
            f"Что вы хотите сделать?",
            state="main"
        )
        self.bot.state_manager.set_state(user_id, "main")
    
    # ============ ГЛАВНОЕ МЕНЮ ============
    
    def handle_main(self, user_id: int, request: str):
        """Главное меню"""
        request_lower = request.lower()
        
        if request_lower == 'профиль':
            user = get_user_by_vk_id(user_id)
            if user:
                sex_str = user.get_sex_str()
                self.bot.send_msg(
                    user_id,
                    f"📋 Ваш профиль:\n\n"
                    f"👤 Имя: {user.first_name}\n"
                    f"🎂 Возраст: {user.age}\n"
                    f"🚻 Пол: {sex_str}\n"
                    f"📍 Город: {user.city}\n"
                    f"🔗 Ссылка: {user.user_vk_link}\n\n"
                    f"Что дальше?",
                    state="main"
                )
            else:
                self.bot.send_msg(user_id, "Профиль не найден", state="main")
                
        elif request_lower == 'смотреть анкеты':
            # Проверяем, заполнен ли профиль
            user = get_user_by_vk_id(user_id)
            if not user or not user.is_profile_complete():
                self.bot.send_msg(
                    user_id,
                    "⚠️ Сначала заполните свой профиль!\n"
                    "Что вы хотите сделать?",
                    state="main"
                )
                return
                
            self.bot.send_msg(
                user_id,
                "🔍 Начинаем поиск анкет...",
                state="dating"
            )
            self.bot.state_manager.set_state(user_id, "dating")
            
        elif request_lower == 'избранные':
            self.bot.send_msg(
                user_id, 
                "⭐ Ваши избранные...\n"
                "Здесь будут отображаться понравившиеся вам анкеты",
                state="main"
            )
            
        elif request_lower == 'чёрный список' or 'чс' in request_lower:
            self.bot.send_msg(
                user_id, 
                "🚫 Ваш черный список...\n"
                "Здесь будут анкеты, которые вы добавили в ЧС",
                state="main"
            )
            
        elif request_lower in ['редактировать профиль', 'изменить профиль', 'настройки']:
            # Предлагаем выбрать, что редактировать
            self.bot.send_msg(
                user_id,
                "Что вы хотите изменить?\n"
                "1 - Имя\n2 - Возраст\n3 - Пол\n4 - Город\n5 - Отмена",
                state=None
            )
            self.bot.state_manager.set_state(user_id, "edit_profile_choice")
            
        elif request_lower == 'помощь' or request_lower == 'help':
            self.bot.send_msg(
                user_id,
                "🤖 Доступные команды:\n\n"
                "📋 Профиль - посмотреть ваш профиль\n"
                "🔍 Смотреть анкеты - начать поиск людей\n"
                "⭐ Избранные - ваши понравившиеся анкеты\n"
                "🚫 Чёрный список - заблокированные анкеты\n"
                "⚙️ Редактировать профиль - изменить данные\n\n"
                "Просто выберите нужный пункт в меню!",
                state="main"
            )
            
        else:
            self.bot.send_msg(
                user_id,
                "Выберите действие из меню:",
                state="main"
            )
    
    # ============ ВЫБОР ЧТО РЕДАКТИРОВАТЬ ============
    
    def handle_edit_profile_choice(self, user_id: int, request: str):
        """Выбор поля для редактирования"""
        request_lower = request.lower()
        
        if request_lower in ['1', 'имя', 'имя']:
            self.bot.send_msg(user_id, "Введите новое имя:", state=None)
            self.bot.state_manager.set_state(user_id, "edit_name")
            
        elif request_lower in ['2', 'возраст', 'лет']:
            self.bot.send_msg(user_id, "Введите новый возраст:", state=None)
            self.bot.state_manager.set_state(user_id, "edit_age")
            
        elif request_lower in ['3', 'пол', 'пол']:
            self.bot.send_msg(
                user_id, 
                "Выберите пол:\n1 - Мужской 👨\n2 - Женский 👩", 
                state=None
            )
            self.bot.state_manager.set_state(user_id, "edit_sex")
            
        elif request_lower in ['4', 'город', 'город']:
            self.bot.send_msg(user_id, "Введите новый город:", state=None)
            self.bot.state_manager.set_state(user_id, "edit_city")
            
        elif request_lower in ['5', 'отмена', 'назад', 'отмена']:
            self.bot.send_msg(user_id, "Возвращаемся в главное меню", state="main")
            self.bot.state_manager.set_state(user_id, "main")
            
        else:
            self.bot.send_msg(
                user_id,
                "Пожалуйста, выберите:\n"
                "1 - Имя\n2 - Возраст\n3 - Пол\n4 - Город\n5 - Отмена",
                state=None
            )
    
    # ============ РЕДАКТИРОВАНИЕ ИМЕНИ ============
    
    def handle_edit_name(self, user_id: int, request: str):
        """Редактирование имени"""
        if len(request.strip()) < 2:
            self.bot.send_msg(user_id, "Имя должно содержать минимум 2 буквы. Попробуйте снова:", state=None)
            return
        
        # Здесь нужно обновить имя в БД
        # save_updated_field(user_id, field='first_name', value=request.strip())
        
        self.bot.send_msg(
            user_id,
            f"✅ Имя изменено на: {request.strip()}",
            state="main"
        )
        self.bot.state_manager.set_state(user_id, "main")
    
    # ============ РЕДАКТИРОВАНИЕ ВОЗРАСТА ============
    
    def handle_edit_age(self, user_id: int, request: str):
        """Редактирование возраста"""
        try:
            age = int(request.strip())
            if age < 14 or age > 100:
                raise ValueError
            
            # Здесь нужно обновить возраст в БД
            # save_updated_field(user_id, field='age', value=age)
            
            self.bot.send_msg(
                user_id,
                f"✅ Возраст изменен на: {age}",
                state="main"
            )
            self.bot.state_manager.set_state(user_id, "main")
                
        except ValueError:
            self.bot.send_msg(
                user_id,
                "Пожалуйста, введите корректный возраст (число от 14 до 100):",
                state=None
            )
    
    # ============ РЕДАКТИРОВАНИЕ ПОЛА ============
    
    def handle_edit_sex(self, user_id: int, request: str):
        """Редактирование пола"""
        request_lower = request.strip().lower()
        sex_map = {
            "1": 2, "2": 1,  # 1-муж, 2-жен (в твоей модели)
            "мужской": 2, "женский": 1,
            "м": 2, "ж": 1
        }
        
        if request_lower in sex_map:
            sex_num = sex_map[request_lower]
            sex_str = "мужской" if sex_num == 2 else "женский"
            
            # Здесь нужно обновить пол в БД
            # save_updated_field(user_id, field='sex', value=sex_num)
            
            self.bot.send_msg(
                user_id,
                f"✅ Пол изменен на: {sex_str}",
                state="main"
            )
            self.bot.state_manager.set_state(user_id, "main")
        else:
            self.bot.send_msg(
                user_id,
                "Пожалуйста, выберите:\n1 - Мужской 👨\n2 - Женский 👩",
                state=None
            )
    
    # ============ РЕДАКТИРОВАНИЕ ГОРОДА ============
    
    def handle_edit_city(self, user_id: int, request: str):
        """Редактирование города"""
        city = request.strip()
        if len(city) < 2:
            self.bot.send_msg(user_id, "Название города должно содержать минимум 2 буквы. Попробуйте снова:", state=None)
            return
        
        # Здесь нужно обновить город в БД
        # save_updated_field(user_id, field='city', value=city)
        
        self.bot.send_msg(
            user_id,
            f"✅ Город изменен на: {city}",
            state="main"
        )
        self.bot.state_manager.set_state(user_id, "main")
    
    # ============ ПРОСМОТР АНКЕТ ============
    
    def handle_dating(self, user_id: int, request: str):
        """Просмотр анкет"""
        request_lower = request.lower()
        
        if request_lower == 'в главное меню':
            self.bot.send_msg(
                user_id,
                "Возвращаемся в главное меню",
                state="main"
            )
            self.bot.state_manager.set_state(user_id, "main")
            
        elif request_lower == 'нравится' or '❤️' in request_lower:
            # Здесь логика добавления в избранное
            # add_to_favorites(user_id, current_profile_id)
            self.bot.send_msg(
                user_id,
                "❤️ Добавлено в понравившиеся!\n"
                "Показываю следующую анкету...",
                state="dating"
            )
            self._show_next_profile(user_id)
            
        elif request_lower == 'не нравится' or '👎' in request_lower:
            # Здесь логика пропуска анкеты
            self.bot.send_msg(
                user_id,
                "👎 Анкета пропущена.\n"
                "Показываю следующую анкету...",
                state="dating"
            )
            self._show_next_profile(user_id)
            
        elif 'добавить в избранное' in request_lower or '⭐' in request_lower:
            # Здесь логика добавления в избранное (отдельная функция)
            # add_to_favorites(user_id, current_profile_id)
            self.bot.send_msg(
                user_id,
                "⭐ Добавлено в избранное!\n"
                "Показываю следующую анкету...",
                state="dating"
            )
            self._show_next_profile(user_id)
            
        elif 'добавить в чс' in request_lower or 'чёрный список' in request_lower or '🚫' in request_lower:
            # Здесь логика добавления в черный список
            # add_to_blacklist(user_id, current_profile_id)
            self.bot.send_msg(
                user_id,
                "🚫 Добавлено в черный список!\n"
                "Показываю следующую анкету...",
                state="dating"
            )
            self._show_next_profile(user_id)
            
        elif 'следующая' in request_lower or 'дальше' in request_lower or '➡️' in request_lower:
            # Просто показываем следующую анкету
            self._show_next_profile(user_id)
            
        elif 'написать' in request_lower or '💌' in request_lower:
            # Здесь логика отправки сообщения
            self.bot.send_msg(
                user_id,
                "💌 Функция отправки сообщения будет доступна позже!\n"
                "Показываю следующую анкету...",
                state="dating"
            )
            self._show_next_profile(user_id)
            
        else:
            # Непонятная команда - показываем текущую анкету
            self._show_next_profile(user_id, show_instructions=True)
    
    def _show_next_profile(self, user_id: int, show_instructions: bool = False):
        """Показать следующую анкету (заглушка)"""
        # TODO: Реализовать получение реальной анкеты
        # profile = get_next_profile(user_id)
        
        message = (
            "👤 Анкета #1:\n\n"
            "Имя: Анна\n"
            "Возраст: 25\n"
            "Город: Москва\n"
            "Интересы: путешествия, музыка, спорт\n\n"
        )
        
        if show_instructions:
            message += (
                "Используйте кнопки для взаимодействия:\n"
                "❤️ - Нравится\n"
                "👎 - Не нравится\n"
                "⭐ - В избранное\n"
                "🚫 - В черный список\n"
                "💌 - Написать сообщение\n"
                "➡️ - Следующая анкета"
            )
        
        self.bot.send_msg(
            user_id,
            message,
            state="dating"
        )
    
    # ============ ИЗБРАННЫЕ ============
    
    def handle_favorites(self, user_id: int, request: str):
        """Просмотр избранных анкет"""
        if request.lower() in ['назад', 'в главное меню', 'меню']:
            self.bot.send_msg(
                user_id,
                "Возвращаемся в главное меню",
                state="main"
            )
            self.bot.state_manager.set_state(user_id, "main")
        else:
            # TODO: Показать список избранных
            self.bot.send_msg(
                user_id,
                "⭐ Ваши избранные анкеты:\n\n"
                "1. Анна, 25 лет, Москва\n"
                "2. Мария, 28 лет, Санкт-Петербург\n"
                "3. Екатерина, 23 года, Казань\n\n"
                "Напишите номер анкеты для просмотра или 'назад' для возврата",
                state=None
            )
    
    # ============ ЧЕРНЫЙ СПИСОК ============
    
    def handle_blacklist(self, user_id: int, request: str):
        """Просмотр черного списка"""
        if request.lower() in ['назад', 'в главное меню', 'меню']:
            self.bot.send_msg(
                user_id,
                "Возвращаемся в главное меню",
                state="main"
            )
            self.bot.state_manager.set_state(user_id, "main")
        else:
            # TODO: Показать черный список
            self.bot.send_msg(
                user_id,
                "🚫 Ваш черный список:\n\n"
                "1. Иван, 30 лет, Москва\n"
                "2. Петр, 35 лет, Санкт-Петербург\n\n"
                "Напишите номер для удаления из списка или 'назад' для возврата",
                state=None
            )