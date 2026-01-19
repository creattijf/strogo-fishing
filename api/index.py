from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

# --- ИЩЕЙКА ДАННЫХ ---
def find_match_object(data):
    if isinstance(data, dict):
        if 'teams' in data and 'i18' in data: return data
        for key, value in data.items():
            result = find_match_object(value)
            if result: return result
    elif isinstance(data, list):
        for item in data:
            result = find_match_object(item)
            if result: return result
    return None

# --- 1. ОНЛАЙН ---
def check_is_fishing(faceit_input):
    try:
        nickname = faceit_input.split('/')[-1] if '/' in faceit_input else faceit_input
        user_res = requests.get(f"https://api.faceit.com/users/v1/nicknames/{nickname}", headers=HEADERS)
        if user_res.status_code != 200: return "error"
        user_id = user_res.json().get('payload', {}).get('id')
        
        match_res = requests.get(f"https://api.faceit.com/match/v1/matches/groupByState?userId={user_id}", headers=HEADERS)
        payload = match_res.json().get('payload', {})
        for state in payload:
            if payload[state] and len(payload[state]) > 0: return True
        return False
    except: return "error"

# --- 2. СТАТИСТИКА + РОСТЕР ---
def get_match_stats_logic(match_url):
    target_nickname = "StRoGo" 
    try:
        if "room/" not in match_url: return {"error": "Неверная ссылка"}
        match_id = match_url.split("room/")[1].split("/")[0]
        
        response = requests.get(f"https://api.faceit.com/stats/v1/stats/matches/{match_id}", headers=HEADERS)
        if response.status_code != 200: return {"error": "Матч не найден"}

        match_data = find_match_object(response.json())
        if not match_data: return {"error": "Данные не найдены"}

        # Переменные
        target_player = None
        my_team_index = -1
        all_players = [] # Список всех игроков для фронтенда

        teams = match_data.get('teams', [])
        if not isinstance(teams, list): teams = []

        for idx, team in enumerate(teams):
            if not isinstance(team, dict): continue
            players = team.get('players', [])
            if not isinstance(players, list): continue

            for player in players:
                if not isinstance(player, dict): continue
                
                p_nick = player.get('nickname', '')
                # Собираем всех игроков: ник и индекс команды (0 или 1)
                all_players.append({
                    "nickname": p_nick,
                    "team_index": idx
                })

                if str(p_nick).lower() == target_nickname.lower():
                    target_player = player
                    my_team_index = idx # 0 или 1

        if not target_player: return {"error": f"Игрок {target_nickname} не найден"}

        # Счет и Результат
        score_obj = match_data.get('i18', '0 / 0')
        match_score_str = score_obj.get('score', '0 / 0') if isinstance(score_obj, dict) else str(score_obj)

        try:
            s = match_score_str.split(' / ')
            s1, s2 = int(s[0]), int(s[1])
        except: s1, s2 = 0, 0

        my_score = s1 if my_team_index == 0 else s2
        enemy_score = s2 if my_team_index == 0 else s1

        result = "WIN" if my_score > enemy_score else ("DRAW" if my_score == enemy_score else "LOSE")

        return {
            "nickname": target_player.get('nickname'),
            "result": result,
            "kills": target_player.get('i6', '0'),
            "deaths": target_player.get('i8', '0'),
            "assists": target_player.get('i7', '0'),
            "kr": target_player.get('c3', '0.0'),
            "kd": target_player.get('c2', '0.0'),
            "hs_percent": target_player.get('c4', '0'),
            "mvp": target_player.get('i9', '0'),
            "score": match_score_str,
            "my_team_index": my_team_index, # Чтобы знать, где свои, где чужие
            "roster": all_players # Отправляем список всех игроков
        }

    except Exception as e:
        print(f"ERR: {e}")
        return {"error": "Ошибка обработки"}

# --- ROUTING ---
@app.route('/api/check_fish', methods=['POST'])
def check_fish():
    status = check_is_fishing(request.json.get('url'))
    return jsonify({"status": "online" if status == True else ("error" if status == "error" else "offline")})

@app.route('/api/get_match_stats', methods=['POST'])
def get_match_stats():
    return jsonify(get_match_stats_logic(request.json.get('url')))

if __name__ == '__main__':
    app.run(debug=True)