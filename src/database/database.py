import psycopg2
from psycopg2.extras import RealDictCursor


class VKinderDatabase:
    def __init__(self):
        self.conn = None
        self.connect()
        self.create_tables()

    def connect(self):
        # Подключение к базе данных
        try:
            self.conn = psycopg2.connect(
                dbname='vkinder',
                user='postgres',
                password='PASSWORD',  #  УБЕДИСЬ ЧТО ПАРОЛЬ ПРАВИЛЬНЫЙ
                host='localhost',
                port='5432'
            )
            print("Успешное подключение к базе данных")
        except Exception as e:
            print(f"Ошибка подключения к базе данных: {e}")

    def create_tables(self):
        # Создание таблиц если их нет
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bot_users (
                        id SERIAL PRIMARY KEY,
                        vk_id INTEGER UNIQUE NOT NULL,
                        first_name VARCHAR(100),
                        last_name VARCHAR(100),
                        age INTEGER,
                        sex INTEGER,
                        city VARCHAR(100),
                        current_state VARCHAR(50) DEFAULT 'start'
                    )
                """)
                self.conn.commit()
                print("Таблица bot_users создана или уже существует")

        except Exception as e:
            print(f"Ошибка при создании таблиц: {e}")
            self.conn.rollback()

    def add_or_update_user(self, vk_id: int, first_name: str, last_name: str,
                           age: int = None, sex: int = None, city: str = None) -> int:
        # Добавление или обновление информации о пользователе
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO bot_users (vk_id, first_name, last_name, age, sex, city)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (vk_id)
                    DO UPDATE SET
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        age = EXCLUDED.age,
                        sex = EXCLUDED.sex,
                        city = EXCLUDED.city
                    RETURNING id
                """, (vk_id, first_name, last_name, age, sex, city))

                user_id = cursor.fetchone()[0]
                self.conn.commit()
                return user_id

        except Exception as e:
            print(f"Ошибка при добавлении или обновлении информации о пользователе: {e}")
            self.conn.rollback()
            return None

    def get_user_state(self, vk_id: int) -> str:
        # Получение состояния пользователя
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT current_state FROM bot_users WHERE vk_id = %s",
                    (vk_id,)
                )
                result = cursor.fetchone()
                return result['current_state'] if result else 'start'

        except Exception as e:
            print(f"Ошибка при получении состояния пользователя: {e}")
            self.conn.rollback()
            return 'start'

    def update_user_state(self, vk_id: int, state: str):
        # Обновление состояния пользователя
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE bot_users SET current_state = %s WHERE vk_id = %s",
                    (state, vk_id)
                )
                self.conn.commit()

        except Exception as e:
            print(f"Ошибка при обновлении состояния пользователя: {e}")
            self.conn.rollback()

    def profile_exists(self, vk_id: int) -> bool:
        # Проверка существования профиля пользователя
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM bot_users WHERE vk_id = %s",
                    (vk_id,)
                )
                return cursor.fetchone() is not None

        except Exception as e:
            print(f"Ошибка при проверке профиля: {e}")
            self.conn.rollback()
            return False

# Тестирование
def test_database():
    db = VKinderDatabase()

    # Тест добавления пользователя
    user_id = db.add_or_update_user(
        vk_id=123456,
        first_name='Иван',
        last_name='Иванов',
        age=25,
        sex=2, # 1 - Женщина, 2 - Мужчина в VK API
        city='Москва'
    )
    print(f"Добавлен пользователь с ID: {user_id}")

    # Тест получения состояния пользователя
    state = db.get_user_state(123456)
    print(f"Текущее состояние пользователя: {state}")

    # Тест обновления состояния пользователя
    db.update_user_state(123456, 'searching')

    # Тест получения состояния пользователя после обновления
    state_after = db.get_user_state(123456)
    print(f"Текущее состояние пользователя после обновления: {state_after}")

if __name__ == "__main__":
    test_database()
