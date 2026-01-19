from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json

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
        
        user_id = user_res.json().get('payload', {}).get('id')
        
        match_url = f"https://api.faceit.com/match/v1/matches/groupByState?userId={user_id}"
        match_res = requests.get(match_url, headers=HEADERS)
        
        data = match_res.json()
        payload = data.get('payload', {})
        for state in payload:
            matches = payload[state]
            if isinstance(matches, list) and len(matches) > 0:
                return True
        return False
    except:
        return "error"

# --- 2. ПОЛУЧЕНИЕ СТАТИСТИКИ (УНИВЕРСАЛЬНАЯ ВЕРСИЯ) ---
def get_match_stats_logic(match_url):
    target_nickname = "StRoGo" 

    try:
        # 1. ID Матча
        if "room/" not in match_url:
            return {"error": "Нужна ссылка на комнату (.../room/ID)"}
        
        match_id = match_url.split("room/")[1].split("/")[0]
        api_url = f"https://api.faceit.com/stats/v1/stats/matches/{match_id}"
        
        print(f"DEBUG: Requesting {api_url}")
        
        response = requests.get(api_url, headers=HEADERS)
        if response.status_code != 200:
            return {"error": f"Ошибка сервера Faceit: {response.status_code}"}

        raw_data = response.json()
        
        # --- ЛОГИКА ПОИСКА ДАННЫХ ---
        # Faceit может вернуть: {"payload": [...]} ИЛИ просто [...]
        
        matches_list = []

        if isinstance(raw_data, dict):
            matches_list = raw_data.get('payload', [])
        elif isinstance(raw_data, list):
            matches_list = raw_data
        else:
            print(f"DEBUG: Unknown data type: {type(raw_data)}")
            return {"error": "Непонятный ответ от Faceit"}

        # Проверяем, есть ли матчи в списке
        if not matches_list or not isinstance(matches_list, list) or len(matches_list) == 0:
            return {"error": "Данные о матче пусты"}

        # Берем первый матч
        match_data = matches_list[0]
        
        # Если это снова список (бывает двойная вложенность)
        if isinstance(match_data, list):
            if len(match_data) > 0:
                match_data = match_data[0]
            else:
                return {"error": "Пустой вложенный список"}

        # Если после всего этого match_data не словарь - беда
        if not isinstance(match_data, dict):
            print(f"DEBUG: match_data is {type(match_data)}")
            return {"error": "Структура матча повреждена"}

        # --- ПАРСИНГ ---
        
        # Победитель
        winner_team_id = None
        elo_data = match_data.get('calculateEloFrom')
        if isinstance(elo_data, dict):
            winner_team_id = elo_data.get('winner')

        # Поиск игрока
        target_player = None
        my_team_id = None
        
        # Защита от отсутствия команд
        teams = match_data.get('teams')
        if not isinstance(teams, list): teams = []

        for team in teams:
            if not isinstance(team, dict): continue
            
            players = team.get('players')
            if not isinstance(players, list): continue

            for player in players:
                if not isinstance(player, dict): continue
                
                # Сравниваем ник
                p_nick = player.get('nickname', '')
                if str(p_nick).lower() == target_nickname.lower():
                    target_player = player
                    my_team_id = team.get('teamId')
                    break
            if target_player: break
        
        if not target_player:
            return {"error": f"Игрок {target_nickname} не найден в этом матче"}

        # Результат
        result = "LOSE"
        if winner_team_id and my_team_id and str(my_team_id) == str(winner_team_id):
            result = "WIN"

        # Счет
        score_val = match_data.get('i18', 'N/A')
        match_score = score_val
        if isinstance(score_val, dict):
            match_score = score_val.get('score', 'N/A')

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
            "score": str(match_score)
        }
        
        return stats

    except Exception as e:
        print(f"DEBUG CRITICAL EXCEPTION: {e}")
        return {"error": "Внутренняя ошибка сервера"}

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