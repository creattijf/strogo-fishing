from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

def check_is_fishing(faceit_input):
    # Настраиваем заголовки, чтобы притвориться браузером
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.faceit.com/"
    }

    try:
        # 1. Вытаскиваем НИКНЕЙМ из ссылки
        nickname = faceit_input
        if "faceit.com" in faceit_input:
            # Если ссылка вида https://www.faceit.com/ru/players/Nickname
            # Разбиваем по слэшам и берем последний кусок
            parts = faceit_input.rstrip('/').split('/')
            nickname = parts[-1]
        
        # 2. Получаем ID игрока (User ID) через API Фейсита
        # Это публичный запрос, который делает сам сайт
        user_url = f"https://api.faceit.com/users/v1/nicknames/{nickname}"
        user_res = requests.get(user_url, headers=headers)
        
        if user_res.status_code != 200:
            print(f"Error finding user: {nickname}")
            return "error"
            
        user_data = user_res.json()
        user_id = user_data.get('payload', {}).get('id')
        
        if not user_id:
            return "error"

        # 3. Проверяем активные матчи для этого ID
        # Этот запрос возвращает список текущих игр (ONGOING, CHECK_IN и т.д.)
        match_url = f"https://api.faceit.com/match/v1/matches/groupByState?userId={user_id}"
        match_res = requests.get(match_url, headers=headers)
        
        if match_res.status_code != 200:
            return False
            
        match_data = match_res.json()
        payload = match_data.get('payload', {})

        # Фейсит возвращает объект, где ключи - это статусы (ONGOING, CHECK_IN, READY)
        # Если в каком-то из этих списков есть данные, значит игрок занят (В пруду)
        
        is_playing = False
        
        # Пробегаемся по всем возможным статусам матча
        for state in payload:
            matches_list = payload[state]
            # Если список матчей в этом статусе не пустой -> Игрок играет
            if matches_list and len(matches_list) > 0:
                is_playing = True
                break
        
        return is_playing

    except Exception as e:
        print(f"Global Error: {e}")
        return "error"

# Маршрут
@app.route('/api/check_fish', methods=['POST'])
def check_fish():
    data = request.json
    url = data.get('url')
    
    # Добавим задержку или повторную попытку здесь не нужно, API отвечает мгновенно
    status = check_is_fishing(url)
    
    if status == "error":
        return jsonify({"status": "error", "message": "Не найден"})
    elif status:
        return jsonify({"status": "online", "message": "В пруду 🎣"})
    else:
        return jsonify({"status": "offline", "message": "Не в пруду ❌"})

if __name__ == '__main__':
    app.run(debug=True)