from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# --- 1. ПРОВЕРКА ОНЛАЙНА ---
def check_is_fishing(faceit_input):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        nickname = faceit_input
        if "faceit.com" in faceit_input:
            parts = faceit_input.rstrip('/').split('/')
            nickname = parts[-1]
        
        user_url = f"https://api.faceit.com/users/v1/nicknames/{nickname}"
        user_res = requests.get(user_url, headers=headers)
        if user_res.status_code != 200: return "error"
        user_id = user_res.json().get('payload', {}).get('id')
        
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

# --- 2. ПОЛУЧЕНИЕ СТАТИСТИКИ (БРОНЕБОЙНАЯ ВЕРСИЯ) ---
def get_match_stats_logic(match_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    target_nickname = "StRoGo" 

    try:
        # 1. Парсинг ID
        if "room/" not in match_url:
            return {"error": "Неверная ссылка"}
        match_id = match_url.split("room/")[1].split("/")[0]

        # 2. Запрос API
        api_url = f"https://api.faceit.com/stats/v1/stats/matches/{match_id}"
        response = requests.get(api_url, headers=headers)
        
        if response.status_code != 200:
            return {"error": "Матч не найден (возможно, еще идет)"}

        json_data = response.json()
        payload = json_data.get('payload')

        # --- ЗАЩИТА ОТ КРИВЫХ ДАННЫХ ---
        # Payload должен быть списком. Если нет - ошибка.
        if not payload or not isinstance(payload, list):
            return {"error": "Нет данных"}

        match_data = payload[0]

        # Если вдруг внутри payload лежит не словарь, а еще один список (бывает и такое)
        if isinstance(match_data, list):
            if len(match_data) > 0:
                match_data = match_data[0]
            else:
                return {"error": "Пустые данные матча"}
        
        # Если после всего этого это не словарь, мы не можем работать
        if not isinstance(match_data, dict):
            return {"error": "Некорректный формат данных от Faceit"}

        # 3. Кто победил
        winner_team_id = None
        elo_info = match_data.get('calculateEloFrom')
        if isinstance(elo_info, dict):
            winner_team_id = elo_info.get('winner')

        # 4. Поиск игрока
        target_player = None
        my_team_id = None
        
        teams = match_data.get('teams', [])
        # Защита: teams должен быть списком
        if not isinstance(teams, list):
            teams = []

        for team in teams:
            if not isinstance(team, dict): continue
            
            players = team.get('players', [])
            if not isinstance(players, list): continue

            for player in players:
                if not isinstance(player, dict): continue
                
                # Сравнение ника
                p_nick = player.get('nickname', '')
                if p_nick and p_nick.lower() == target_nickname.lower():
                    target_player = player
                    my_team_id = team.get('teamId')
                    break
            if target_player: break
        
        if not target_player:
            return {"error": f"Игрок {target_nickname} не найден в этом матче"}

        # 5. Результат
        result = "LOSE"
        # Приводим к строке, чтобы сравнение было точным (иногда приходят int, иногда str)
        if winner_team_id and my_team_id and str(my_team_id) == str(winner_team_id):
            result = "WIN"

        # 6. Счет
        score_info = match_data.get('i18', 'N/A')
        match_score = score_info
        if isinstance(score_info, dict):
            match_score = score_info.get('score', 'N/A')

        # Сборка ответа
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
        # Выводим ошибку в консоль сервера для отладки
        print(f"CRITICAL ERROR parsing: {e}")
        return {"error": "Ошибка обработки данных"}

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