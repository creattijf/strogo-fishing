from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# --- 1. ПРОВЕРКА ОНЛАЙНА (Старая функция) ---
def check_is_fishing(faceit_input):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.faceit.com/"
    }
    try:
        nickname = faceit_input
        if "faceit.com" in faceit_input:
            parts = faceit_input.rstrip('/').split('/')
            nickname = parts[-1]
        
        # Получаем ID
        user_url = f"https://api.faceit.com/users/v1/nicknames/{nickname}"
        user_res = requests.get(user_url, headers=headers)
        if user_res.status_code != 200: return "error"
        user_id = user_res.json().get('payload', {}).get('id')
        if not user_id: return "error"

        # Проверяем матчи
        match_url = f"https://api.faceit.com/match/v1/matches/groupByState?userId={user_id}"
        match_res = requests.get(match_url, headers=headers)
        if match_res.status_code != 200: return False
        
        payload = match_res.json().get('payload', {})
        for state in payload:
            if payload[state] and len(payload[state]) > 0:
                return True
        return False
    except:
        return "error"

# --- 2. ПОЛУЧЕНИЕ СТАТИСТИКИ МАТЧА (Новая функция) ---
def get_match_stats_logic(match_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    target_nickname = "StRoGo" # Ищем ТОЛЬКО этого игрока

    try:
        # Вытаскиваем Match ID из ссылки
        # Ссылка вида: .../room/1-54cc7dd5-fc1e...
        if "room/" not in match_url:
            return {"error": "Неверная ссылка"}
        
        match_id = match_url.split("room/")[1].split("/")[0]

        # Запрос к API статистики
        api_url = f"https://api.faceit.com/stats/v1/stats/matches/{match_id}"
        response = requests.get(api_url, headers=headers)
        
        if response.status_code != 200:
            return {"error": "Матч не найден или еще идет"}

        data = response.json().get('payload', [])
        if not data:
            return {"error": "Нет данных"}

        match_data = data[0] # Берем первый (единственный) матч
        
        # Ищем StRoGo в командах
        target_player = None
        my_team_id = None
        winner_team_id = match_data.get('calculateEloFrom', {}).get('winner') # Кто победил

        # Пробегаемся по командам
        for team in match_data.get('teams', []):
            for player in team.get('players', []):
                # Сравниваем ник (регистр не важен)
                if player.get('nickname').lower() == target_nickname.lower():
                    target_player = player
                    my_team_id = team.get('teamId')
                    break
            if target_player: break
        
        if not target_player:
            return {"error": f"Игрок {target_nickname} не найден в этом матче"}

        # Определяем результат
        result = "LOSE"
        if my_team_id == winner_team_id:
            result = "WIN"

        # Собираем статистику
        stats = {
            "nickname": target_player.get('nickname'),
            "result": result,
            "kills": target_player.get('i6'),
            "deaths": target_player.get('i8'),
            "assists": target_player.get('i7'),
            "kr": target_player.get('c3'),  # K/R Ratio
            "kd": target_player.get('c2'),  # K/D Ratio
            "hs_percent": target_player.get('c4'), # HS %
            "mvp": target_player.get('i9'),
            "score": f"{match_data.get('i18', {}).get('score')}" # Счет матча (строка "13 / 10")
        }
        
        return stats

    except Exception as e:
        print(e)
        return {"error": "Ошибка обработки"}

# --- МАРШРУТЫ ---

@app.route('/api/check_fish', methods=['POST'])
def check_fish():
    data = request.json
    status = check_is_fishing(data.get('url'))
    if status == "error": return jsonify({"status": "error"})
    elif status: return jsonify({"status": "online"})
    else: return jsonify({"status": "offline"})

@app.route('/api/get_match_stats', methods=['POST'])
def get_match_stats():
    data = request.json
    stats = get_match_stats_logic(data.get('url'))
    return jsonify(stats)

if __name__ == '__main__':
    app.run(debug=True)