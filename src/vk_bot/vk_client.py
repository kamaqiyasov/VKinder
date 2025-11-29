from datetime import datetime
import requests


class VKUser:

    def __init__(self, access_token, user_id, version='5.131'):
        self.token = access_token
        self.id = user_id
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}

    def user_info(self):
        url = 'https://api.vk.com/method/users.get'
        params = {
            'user_ids': self.id,
            'fields': 'bdate,city,sex'
        }
        try:
            response = requests.get(url, params={**self.params, **params})
            response.raise_for_status()
            data = response.json()

            if 'error' in data:
                raise Exception(f"VK API Error: {data['error']}")

            user = data.get('response', [{}])[0]

            age = None
            if 'bdate' in user and len(user['bdate'].split('.')) == 3:
                b = datetime.strptime(user['bdate'], "%d.%m.%Y")
                age = int((datetime.now() - b).days / 365.25)

            gender = None
            if user.get('sex') == 1:
                gender = 'Женский'
            elif user.get('sex') == 2:
                gender = 'Мужской'

            city = user.get('city', {}).get('title')

            return {
                'vk_id': user['id'],
                'first_name': user.get('first_name'),
                'last_name': user.get('last_name'),
                'age': age,
                'gender': gender,
                'city': city,
                'vk_link': f"https://vk.com/id{user['id']}"
            }

        except Exception as e:
            print(f"Ошибка VK API: {e}")
            return None