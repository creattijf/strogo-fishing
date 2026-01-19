from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# --- ПРОВЕРКА ОНЛАЙНА ---
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

# --- ПОЛУЧЕНИЕ СТАТИСТИКИ (ИСПРАВЛЕНО) ---
def get_match_stats_logic(match_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    # ВАЖНО: Ищем именно этого игрока
    target_nickname = "StRoGo"

    try:
        # 1. Достаем ID матча из ссылки
        if "room/" not in match_url:
            return {"error": "Это не ссылка на комнату"}
        
        # Ссылка может быть разной, берем кусок после room/
        match_id = match_url.split("room/")[1].split("/")[0]

        # 2. Запрос к статистике
        api_url = f"https://api.faceit.com/stats/v1/stats/matches/{match_id}"
        response = requests.get(api_url, headers=headers)
        
        if response.status_code != 200:
            return {"error": "Матч не найден или статистика еще не готова"}

        json_resp = response.json()
        payload = json_resp.get('payload')

        # Защита от ошибки 'list object has no attribute get'
        if not payload or not isinstance(payload, list):
            return {"error": "Нет данных"}

        match_data = payload[0] # Берем первый элемент списка

        # 3. Определяем победителя
        # calculateEloFrom может быть списком [], поэтому проверяем тип
        winner_team_id = None
        elo_info = match_data.get('calculateEloFrom')
        if isinstance(elo_info, dict):
            winner_team_id = elo_info.get('winner')

        # 4. Ищем StRoGo
        target_player = None
        my_team_id = None
        
        # Перебираем команды
        teams = match_data.get('teams', [])
        for team in teams:
            players = team.get('players', [])
            for player in players:
                # Сравниваем ник
                if player.get('nickname', '').lower() == target_nickname.lower():
                    target_player = player
                    my_team_id = team.get('teamId')
                    break
            if target_player: break
        
        if not target_player:
            return {"error": f"Игрок {target_nickname} не играл в этом матче"}

        # 5. Результат (Победа/Поражение)
        result = "LOSE"
        if winner_team_id and my_team_id and str(my_team_id) == str(winner_team_id):
            result = "WIN"

        # 6. Счет матча
        # Иногда i18 это строка, иногда словарь. Проверяем.
        score_raw = match_data.get('i18', 'N/A')
        match_score = score_raw
        if isinstance(score_raw, dict):
            match_score = score_raw.get('score', 'N/A')

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
            "score": match_score
        }
        
        return stats

    except Exception as e:
        print(f"Error: {e}")
        return {"error": "Ошибка обработки данных"}

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