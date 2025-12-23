import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from src.database.crud import (
    get_user_by_vk_id,
    get_or_create_search_settings,
    add_interaction,
    get_interactions
)
from src.vk_bot.keyboards import get_search_keyboard, get_main_keyboard
from src.vk_bot.vk_client import VKClient

logger = logging.getLogger(__name__)


class SearchHandlers:
    
    def __init__(self, vk_client: VKClient, api, send_message_callback=None) -> None:
        self.api = api
        self.send_message = send_message_callback
        self.vk_client = vk_client
        self.search_sessions: Dict[int, Dict] = {}
        
    def start_search(self, vk_id: int) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Запускает поиск и показывает первого кандидата"""
        logger.info(f"Запуск поиска для пользователя {vk_id}")
        
        # Получаем пользователя из базы
        user = get_user_by_vk_id(vk_id)
        if not user:
            return "Ошибка получения пользователя", None, None
        
        # Получаем настройки поиска
        settings = get_or_create_search_settings(user.id)
        if not settings:
            return "Ошибка получения настроек поиска", None, None
        
        # Vk_id тех, кого исключаем
        exclude_ids = [inter.vk_id for inter in get_interactions(user.id)]                 
        exclude_ids.append(vk_id)
        logger.info(f"Исключаем {len(exclude_ids)} пользователей из поиска")
        
        # Формируем параметры для VK API
        search_params = self._build_search_params(settings)
                
        try:
            # vk_results = self.vk_client.search_users(**search_params)
            all_results = self._get_all_search_results(search_params)
            exit()
            logger.info(f"VK API вернул {len(all_results)} результатов")
        except Exception as e:
            logger.error(f"Ошибка VK API: {e}")
            return "Ошибка при поиске. Попробуйте позже.", None, None
        
        # Фильтруем результаты
        filtered_results = self._filter_search_results(all_results, exclude_ids)
        logger.info(f"После фильтрации осталось {len(filtered_results)} кандидатов")
        
        # Сохраняем сессию поиска
        self.search_sessions[vk_id] = {
            'results': filtered_results,
            'index': 0,
            'bot_user_id': user.id,
            'created_at': datetime.now()
        }
        
        # Показываем первого кандидата
        return self._show_current_candidate(vk_id)
    
    def _get_all_search_results(self, params: Dict) -> List[Dict]:
        """Получает пользователей пачками по 100 с увеличением offset"""
        
        all_users = []
        offset = 0
        
        while True:
            # Устанавливаем параметры для текущего запроса
            current_params = params.copy()
            current_params['count'] = 100
            current_params['offset'] = offset
            
            logger.info(f"Запрос: offset={offset}, count=100")
            
            try:
                # Делаем запрос к VK API
                response = self.vk_client.search_users(**current_params)
                
                # Получаем список пользователей
                if isinstance(response, dict):
                    batch = response.get('items', [])
                else:
                    batch = response
                
                print(len(batch))
                
                # Если нет пользователей - выходим
                if not batch:
                    logger.info(f"Нет пользователей на offset {offset}")
                    break
                
                # Добавляем пользователей в общий список
                all_users.extend(batch)
                logger.info(f"Получили {len(batch)} пользователей, всего: {len(all_users)}")
                
                # Если получили меньше 100, значит это последняя пачка
                if len(batch) < 100:
                    logger.info("Это последняя пачка")
                    break
                
                # Увеличиваем offset для следующего запроса
                offset += 100
                
                # Делаем паузу между запросами
                import time
                time.sleep(0.34)
                
            except Exception as e:
                logger.error(f"Ошибка при запросе: {e}")
                break
        
        logger.info(f"Всего получено: {len(all_users)} пользователей")
        return all_users
    
    def get_candidate_attachment(self, candidate_data: Dict) -> Optional[str]:
        """Формирует attachment для фото кандидата"""
        if not candidate_data:
            return None
        
        photos = candidate_data.get('photos', [])
        if not photos:
            return None
        
        attachments = []
        for photo in photos:
            owner_id = photo.get('owner_id')
            photo_id = photo.get('id')
            
            if owner_id and photo_id:
                attachments.append(f"photo{owner_id}_{photo_id}")
        
        if attachments:
            return ",".join(attachments)
        
        return None
        
    def handle_search_command(self, user_id: int, command: str) -> Tuple[Optional[str], Optional[str], Optional[Dict]]:
        """Обрабатывает команды в режиме поиска"""
        if user_id not in self.search_sessions:
            return None, None, None
        
        command_lower = command.lower().strip()
        session = self.search_sessions[user_id]
        
        if command_lower == 'дальше':
            # Отмечаем текущего как просмотренного
            self._mark_current_as_viewed(user_id)
            # Переходим к следующему
            session['index'] += 1
            return self._show_current_candidate(user_id)
        
        elif command_lower == 'в избранное':
            # Добавляем в избранное
            self._add_to_favorites(user_id)
            if self.send_message:
                self.send_message(user_id, "Добавлено в избранное!")
            # И переходим к следующему
            session['index'] += 1
            return self._show_current_candidate(user_id)        
        elif command_lower == 'в черный список':
            # Добавляем в ЧС
            self._add_to_blacklist(user_id)
            if self.send_message:
                self.send_message(user_id, "Добавлено в черный спискок!")
            # И переходим к следующему
            session['index'] += 1
            return self._show_current_candidate(user_id)           
        elif command_lower == 'главное меню':
            # Завершаем поиск
            del self.search_sessions[user_id]
            return "Выход из режима поиска", get_main_keyboard(), None
        
        return "Используйте кнопки для управления поиском", get_search_keyboard(), None
    
    def is_in_search_mode(self, user_id: int) -> bool:
        """Проверяет, находится ли пользователь в режиме поиска"""
        return user_id in self.search_sessions

    def _build_search_params(self, settings) -> Dict:
        """Формирует параметры для VK API поиска из SearchSettings"""
        params = {
            'sort': 0,
            'fields': 'photo_orig,photo_id,city,sex,bdate,can_access_closed',
            'status': 1,
            'has_photo': 1 if settings.has_photo else 0,
        }
        
        if settings.sex in [1, 2]:
            params['sex'] = settings.sex
        params['age_from'] = settings.age_from
        params['age_to'] = settings.age_to
        
        if settings.city:
            params['hometown'] = settings.city
        
        logger.info(f"Параметры поиска: {params}")
        return params
        
    
    def _filter_search_results(self, results: List[Dict], exclude_ids: List[int]) -> List[Dict]:
        """Фильтрует результаты поиска"""
        filtered = []
        
        for candidate in results:
            cand_id = candidate.get('id')
            
            # Проверяем исключения
            if not cand_id or cand_id in exclude_ids:
                continue
            
            # Пропускаем закрытые профили
            if candidate.get('is_closed', True):
                continue
            
            # Проверяем доступ к профилю
            if not candidate.get('can_access_closed', True):
                continue
            
            filtered.append(candidate)
        
        return filtered

    def _show_current_candidate(self, vk_id: int) -> Tuple[str, Optional[str], Optional[Dict]]:
        """Показывает текущего кандидата из сессии"""
        if vk_id not in self.search_sessions:
            return "Поиск не активен", None, None
        
        session = self.search_sessions[vk_id]
        current_idx = session['index']
        results = session['results']
        
        logger.info(f"Пользователь {vk_id}: показ кандидата {current_idx + 1} из {len(results)}")
        
        # Проверяем, есть ли еще кандидаты
        if current_idx >= len(results):
            del self.search_sessions[vk_id]
            return "Кандидаты закончились!\nНачните новый поиск.", get_main_keyboard(), None
        
        # Берем текущего кандидата
        candidate = results[current_idx]
        
        photos = []
        candidate_id = candidate.get('id')
        photos = self.vk_client.get_popular_profile_photos(candidate_id, count=3)

        # Формируем сообщение
        message = self._format_candidate_message(candidate)
        
        # Возвращаем данные кандидата
        candidate_data = {
            'vk_id': candidate.get('id'),
            'first_name': candidate.get('first_name', ''),
            'last_name': candidate.get('last_name', ''),
            'age': self._calculate_age(candidate.get('bdate')),
            'city': candidate.get('city', {}).get('title') if candidate.get('city') else None,
            'photos': photos,
            'profile_link': f"https://vk.com/id{candidate.get('id')}"
        }
        
        return message, get_search_keyboard(), candidate_data
    
    def _format_candidate_message(self, candidate: Dict) -> str:
        """Форматирует сообщение с информацией о кандидате"""
        lines = []
        
        # Имя
        first_name = candidate.get('first_name', '')
        last_name = candidate.get('last_name', '')
        if first_name or last_name:
            lines.append(f"{first_name} {last_name}")
        
        # Возраст
        age = self._calculate_age(candidate.get('bdate'))
        if age:
            lines.append(f"{age} лет")
        
        # Город
        city = candidate.get('city', {}).get('title') if candidate.get('city') else None
        if city:
            lines.append(f"{city}")
        
        # Ссылка
        vk_id = candidate.get('id')
        if vk_id:
            lines.append(f"\n vk.com/id{vk_id}")
        
        # lines.append("\nВыберите действие:")
        
        return "\n".join(lines)
    
    def _calculate_age(self, bdate: Optional[str]) -> Optional[int]:
        """Вычисляет возраст из даты рождения"""
        if not bdate:
            return None
        
        try:
            parts = bdate.split('.')
            if len(parts) != 3:
                return None
            
            day, month, year = map(int, parts)
            today = datetime.now()
            age = today.year - year
            
            # Корректируем, если день рождения еще не наступил
            if (today.month, today.day) < (month, day):
                age -= 1
            
            return age if age > 0 else None
        except:
            return None
    
    def _mark_current_as_viewed(self, user_id: int) -> None:
        """Добавляет текущего кандидата в просмотренные"""
        if user_id not in self.search_sessions:
            return
        
        session = self.search_sessions[user_id]
        current_idx = session['index']
        results = session['results']
        
        if current_idx >= len(results):
            return
        
        candidate = results[current_idx]
        
        add_interaction(
            bot_user_id=session['bot_user_id'],
            vk_id=candidate['id'],
            interaction_type='viewed',
            vk_name=f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}",
            profile_link=f"https://vk.com/id{candidate['id']}"
        )
    
    def _add_to_favorites(self, user_id: int) -> None:
        """Добавляет текущего кандидата в избранное"""
        if user_id not in self.search_sessions:
            return
        
        session = self.search_sessions[user_id]
        current_idx = session['index']
        results = session['results']
        
        if current_idx >= len(results):
            return
        
        candidate = results[current_idx]
        
        add_interaction(
            bot_user_id=session['bot_user_id'],
            vk_id=candidate['id'],
            interaction_type='favorite',
            vk_name=f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}",
            profile_link=f"https://vk.com/id{candidate['id']}",
            photos={'photo_max': candidate.get('photo_max_orig')}
        )
    
    def _add_to_blacklist(self, user_id: int) -> None:
        """Добавляет текущего кандидата в черный список"""
        if user_id not in self.search_sessions:
            return
        
        session = self.search_sessions[user_id]
        current_idx = session['index']
        results = session['results']
        
        if current_idx >= len(results):
            return
        
        candidate = results[current_idx]
        
        add_interaction(
            bot_user_id=session['bot_user_id'],
            vk_id=candidate['id'],
            interaction_type='blacklist',
            vk_name=f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}",
            profile_link=f"https://vk.com/id{candidate['id']}"
        )
    
    def cleanup_old_sessions(self, hours_old: int = 1) -> None:
        """Очищает старые сессии поиска"""
        cutoff_time = datetime.now() - timedelta(hours=hours_old)
        
        to_delete = []
        for user_id, session in self.search_sessions.items():
            if session['created_at'] < cutoff_time:
                to_delete.append(user_id)
        
        for user_id in to_delete:
            del self.search_sessions[user_id]
        
        if to_delete:
            logger.info(f"Очищено {len(to_delete)} старых сессий поиска")