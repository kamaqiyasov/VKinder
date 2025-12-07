from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

# Создаём папку для токенов
os.makedirs('tokens', exist_ok=True)

@app.route('/')
def home():
    return '''
    <h1>✅ VK Token Server</h1>
    <p>Сервер для получения токенов VK</p>
    <p>Callback URL: <code>/vk_callback</code></p>
    '''

@app.route('/vk_callback')
def vk_callback():
    """Сюда VK пришлёт токен после авторизации"""
    
    # Получаем токен из URL
    token = request.args.get('access_token')
    user_id = request.args.get('user_id')
    
    if token and user_id:
        # Сохраняем в файл
        data = {
            'user_id': user_id,
            'access_token': token,
            'created': datetime.now().isoformat()
        }
        
        with open(f'tokens/{user_id}.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Сохранён токен для user_id={user_id}")
        
        return '''
        <html>
        <body style="text-align: center; padding: 50px; font-family: Arial;">
            <h2 style="color: green;">✅ Готово!</h2>
            <p>Токен получен и сохранён.</p>
            <p>Окно закроется через 2 секунды...</p>
            <script>
                setTimeout(function() {
                    window.close();
                }, 2000);
            </script>
        </body>
        </html>
        '''
    
    return "❌ Не получилось", 400

@app.route('/get_token/<user_id>')
def get_token(user_id):
    """Получить токен пользователя (для бота)"""
    try:
        with open(f'tokens/{user_id}.json', 'r') as f:
            return jsonify(json.load(f))
    except:
        return jsonify({'error': 'Токен не найден'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))