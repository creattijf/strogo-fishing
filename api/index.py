from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

# --- 1. ПРОВЕРКА ОНЛАЙНА ---
def check_is_fishing(faceit_input):
    try:
        nickname = faceit_input
        if "faceit.com" in faceit_input:
            parts = faceit_input.rstrip('/').split('/')
            nickname = parts[-1]
        
        user_url = f"https://api.faceit.com/users/v1/nicknames/{nickname}"
        user_res = requests.get(user_url, headers=HEADERS)
        if user_res.status_code != 200: return "error"
        
        user_data = user_res.json()
        if not isinstance(user_data, dict): return "error"
        user_id = user_data.get('payload', {}).get('id')
        
        match_url = f"https://api.faceit.com/match/v1/matches/groupByState?userId={user_id}"
        match_res = requests.get(match_url, headers=HEADERS)
        
        data = match_res.json()
        if not isinstance(data, dict): return False
        payload = data.get('payload', {})
        
        for state in payload:
            matches = payload[state]
            if isinstance(matches, list) and len(matches) > 0:
                return True
        return False
    except:
        return "error"

# --- 2. ПОЛУЧЕНИЕ СТАТИСТИКИ (ЛОГИКА ПО СЧЕТУ) ---
def get_match_stats_logic(match_url):
    target_nickname = "StRoGo" 

    try:
        # 1. Ссылка -> ID
        if "room/" not in match_url:
            return {"error": "Нужна ссылка на комнату"}
        
        match_id = match_url.split("room/")[1].split("/")[0]
        api_url = f"https://api.faceit.com/stats/v1/stats/matches/{match_id}"
        
        response = requests.get(api_url, headers=HEADERS)
        if response.status_code != 200:
            return {"error": "Матч не найден"}

        raw_data = response.json()
        payload = raw_data.get('payload')

        # Защита от кривых данных
        match_data = None
        if isinstance(payload, list) and len(payload) > 0:
            match_data = payload[0]
            if isinstance(match_data, list): match_data = match_data[0] # Если двойной список
        elif isinstance(payload, dict):
            match_data = payload

        if not isinstance(match_data, dict):
            return {"error": "Ошибка структуры данных"}

        # 2. Ищем игрока и ОПРЕДЕЛЯЕМ ИНДЕКС КОМАНДЫ (0 или 1)
        target_player = None
        my_team_index = -1 # 0 - это первая команда, 1 - это вторая
        
        teams = match_data.get('teams', [])
        if not isinstance(teams, list): teams = []

        # Пробегаемся по командам с индексом (idx)
        for idx, team in enumerate(teams):
            if not isinstance(team, dict): continue
            
            players = team.get('players', [])
            if not isinstance(players, list): continue

            for player in players:
                if not isinstance(player, dict): continue
                
                # Сравниваем ник
                p_nick = player.get('nickname', '')
                if str(p_nick).lower() == target_nickname.lower():
                    target_player = player
                    my_team_index = idx # Запоминаем: мы в первой (0) или второй (1) команде
                    break
            if target_player: break
        
        if not target_player:
            return {"error": f"Игрок {target_nickname} не найден в матче"}

        # 3. Достаем СЧЕТ и определяем победителя
        score_obj = match_data.get('i18', '0 / 0')
        match_score_str = "0 / 0"
        
        if isinstance(score_obj, dict):
            match_score_str = score_obj.get('score', '0 / 0')
        elif isinstance(score_obj, str):
            match_score_str = score_obj

        # Парсим строку "13 / 9"
        try:
            scores = match_score_str.split(' / ')
            team1_score = int(scores[0])
            team2_score = int(scores[1])
        except:
            team1_score = 0
            team2_score = 0

        # Логика: 
        # Если мы в команде 0, то наш счет - это team1_score
        # Если мы в команде 1, то наш счет - это team2_score
        
        my_score = 0
        enemy_score = 0
        
        if my_team_index == 0:
            my_score = team1_score
            enemy_score = team2_score
        else:
            my_score = team2_score
            enemy_score = team1_score

        # Финальное решение
        result = "LOSE"
        if my_score > enemy_score:
            result = "WIN"
        elif my_score == enemy_score:
            result = "DRAW" # Ничья (редко, но бывает)

        stats = {
            "nickname": target_player.get('nickname'),
            "result": result,
            "kills": target_player.get('i6', '0'),
            "deaths": target_player.get('i8', '0'),
            "assists": target_player.get('i7', '0'),
            "kr": target_player.get('c3', '0.0'),
            "kd": target_player.get('c2', '0.0'),
            "hs_percent": target_player.get('c4', '0'),
            "mvp": target_player.get('i9', '0'),
            "score": match_score_str
        }
        
        return stats

    except Exception as e:
        print(f"Error: {e}")
        return {"error": "Ошибка обработки"}

# --- ROUTING ---

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