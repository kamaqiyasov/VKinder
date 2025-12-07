import webbrowser
import requests
import json

CLIENT_ID = "54388226"
SCOPES = "friends"

print("🔗 Авторизация мини-приложения VK")
print("=" * 50)

# Правильный URL для мини-приложения
auth_url = (
    f"https://oauth.vk.com/authorize?"
    f"client_id={CLIENT_ID}&"
    f"display=page&"
    f"redirect_uri=https://oauth.vk.com/blank.html&"
    f"response_type=token&"
    f"scope={SCOPES}&"
    f"v=5.199&"
    f"state=mini_app"
)

print(f"URL: {auth_url}")
print("\nОткрываю в браузере...")
webbrowser.open(auth_url)

print("\n📋 После авторизации:")
print("1. Скопируйте access_token из адресной строки")
print("Пример: https://oauth.vk.com/blank.html#access_token=ваш_токен...")
print("2. Вставьте его ниже\n")

access_token = input("Введите access_token: ").strip()

# Проверка
print("\n🔍 Проверяю токен...")
response = requests.get(
    "https://api.vk.com/method/users.get",
    params={"access_token": access_token, "v": "5.199"}
).json()

if "response" in response:
    user = response["response"][0]
    print(f"✅ Успех! Пользователь: {user['first_name']} {user['last_name']}")
    
    # Проверка users.search
    print("\n🔎 Проверяю users.search...")
    search_response = requests.get(
        "https://api.vk.com/method/users.search",
        params={
            "access_token": access_token,
            "q": "Иван",
            "count": 2,
            "v": "5.199"
        }
    ).json()
    
    print("Результат:")
    print(json.dumps(search_response, indent=2, ensure_ascii=False))
    
else:
    print(f"❌ Ошибка: {response}")