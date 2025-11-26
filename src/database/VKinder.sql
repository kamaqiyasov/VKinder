-- Таблица с пользователями бота
create table bot_users (
	id SERIAL primary key,
	vk_id integer unique not null,
	first_name VARCHAR(100),
	last_name VARCHAR(100),
	age integer,
	sex integer,
	city VARCHAR(100),
	current_state VARCHAR(50) default 'start'
	);

-- Таблица для найденных анкет
create table profiles (
	id SERIAL primary key,
	vk_id integer unique not null,
	first_name VARCHAR(100),
	last_name VARCHAR(100),
	profile_url VARCHAR(255),
	age integer,
	sex integer,
	city VARCHAR(100)
	);

-- Таблица для фотографий
create table photos (
	id SERIAL primary key,
	profile_id integer references profiles(id),
	photo_url VARCHAR(255) not null,
	likes_count integer default 0
	);
	
-- Таблица избранных
create table favorites (
	id SERIAL primary key,
	bot_user_id integer references bot_users(id),
	profile_id integer references profiles(id),
	added_at timestamp default current_timestamp,
	unique(bot_user_id, profile_id)
	);

-- Таблица черного списка
create table blacklist (
	id SERIAL primary key,
	bot_user_id integer references bot_users(id),
	profile_id integer references profiles(id),
	added_at timestamp default current_timestamp,
	unique(bot_user_id, profile_id)
	);
	