-- Таблица с пользователями бота
CREATE TABLE bot_users (
    id SERIAL PRIMARY KEY,
    vk_id INTEGER UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    age INTEGER,
    sex INTEGER, -- 1 - женский, 2 - мужской (как в VK API)
    city VARCHAR(100)
);

-- Таблица для хранения состояний пользователей
CREATE TABLE user_states (
    id SERIAL PRIMARY KEY,
    vk_id INTEGER UNIQUE NOT NULL,
    current_state VARCHAR(50) DEFAULT 'start',
    state_data JSONB DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для найденных анкет
CREATE TABLE profiles (
    id SERIAL PRIMARY KEY,
    vk_id INTEGER UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    profile_url VARCHAR(255),
    age INTEGER,
    sex INTEGER, -- 1 - женский, 2 - мужской
    city VARCHAR(100)
);

-- Таблица для фотографий
CREATE TABLE photos (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
    photo_url VARCHAR(500) NOT NULL,
    likes_count INTEGER DEFAULT 0,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица избранных
CREATE TABLE favorites (
    id SERIAL PRIMARY KEY,
    bot_user_id INTEGER REFERENCES bot_users(id) ON DELETE CASCADE,
    profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bot_user_id, profile_id)
);

-- Таблица черного списка
CREATE TABLE blacklist (
    id SERIAL PRIMARY KEY,
    bot_user_id INTEGER REFERENCES bot_users(id) ON DELETE CASCADE,
    profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bot_user_id, profile_id)
);

-- Таблица предпочтений поиска
CREATE TABLE search_preferences (
    id SERIAL PRIMARY KEY,
    bot_user_id INTEGER REFERENCES bot_users(id) ON DELETE CASCADE UNIQUE,
    search_sex INTEGER, -- 1 - женский, 2 - мужской, 3 - любой
    search_age_min INTEGER DEFAULT 18,
    search_age_max INTEGER DEFAULT 99,
    search_city VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для истории просмотров
CREATE TABLE viewed_profiles (
    id SERIAL PRIMARY KEY,
    bot_user_id INTEGER REFERENCES bot_users(id) ON DELETE CASCADE,
    profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bot_user_id, profile_id)
);
-- Таблица для лайков фотографий
CREATE TABLE photo_likes (
    id SERIAL PRIMARY KEY,
    bot_user_id INTEGER REFERENCES bot_users(id) ON DELETE CASCADE,
    profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
    photo_url VARCHAR(500) NOT NULL,
    liked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bot_user_id, photo_url)
);