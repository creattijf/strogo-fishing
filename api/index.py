from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json

app = Flask(__name__)
CORS(app)

# Имитируем настоящий браузер, чтобы Faceit не блокировал
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
    "Referer": "https://www.faceit.com/",
    "Origin": "https://www.faceit.com"
}

# --- 1. ПРОВЕРКА ОНЛАЙНА ---
def check_is_fishing(faceit_input):
    try:
        nickname = faceit_input
        if "faceit.com" in faceit_input:
            parts = faceit_input.rstrip('/').split('/')
            nickname = parts[-1]
        
        # 1. Получаем ID игрока
        user_url = f"https://api.faceit.com/users/v1/nicknames/{nickname}"
        user_res = requests.get(user_url, headers=HEADERS)
        
        if user_res.status_code != 200: return "error"
        user_data = user_res.json()
        user_id = user_data.get('payload', {}).get('id')
        
        if not user_id: return "error"

        # 2. Проверяем матчи
        match_url = f"https://api.faceit.com/match/v1/matches/groupByState?userId={user_id}"
        match_res = requests.get(match_url, headers=HEADERS)
        
        if match_res.status_code != 200: return False
        
        payload = match_res.json().get('payload', {})
        for state in payload:
            matches = payload[state]
            if isinstance(matches, list) and len(matches) > 0:
                return True
        return False
    except:
        return "error"

# --- 2. ПОЛУЧЕНИЕ СТАТИСТИКИ (StRoGo) ---
def get_match_stats_logic(match_url):
    target_nickname = "StRoGo" 

    try:
        # 1. Получаем ID матча
        if "room/" not in match_url:
            return {"error": "Ссылка должна содержать /room/..."}
        
        match_id_part = match_url.split("room/")[1]
        match_id = match_id_part.split("/")[0] # Берём ID до следующего слэша

        # 2. Запрос к API
        api_url = f"https://api.faceit.com/stats/v1/stats/matches/{match_id}"
        print(f"Requesting: {api_url}") # Лог в консоль сервера
        
        response = requests.get(api_url, headers=HEADERS)
        
        # Если статус не 200, выводим код ошибки
        if response.status_code != 200:
            return {"error": f"Faceit API вернул код {response.status_code}"}

        # Пытаемся распарсить JSON
        try:
            json_data = response.json()
        except json.JSONDecodeError:
            return {"error": "Faceit вернул не JSON (возможно, защита от ботов)"}

        # Проверяем, что пришел словарь
        if not isinstance(json_data, dict):
            return {"error": f"Странный ответ API: {type(json_data)}"}

        payload = json_data.get('payload')

        # Если payload пустой -> матч есть, но статы нет (отменен или еще идет)
        if not payload:
            return {"error": "Статистика матча еще не готова или недоступна"}

        # Нормализация данных (список или словарь?)
        match_data = None
        if isinstance(payload, list):
            if len(payload) > 0:
                match_data = payload[0]
                # Двойная вложенность (бывает редко)
                if isinstance(match_data, list) and len(match_data) > 0:
                    match_data = match_data[0]
        elif isinstance(payload, dict):
            match_data = payload

        if not isinstance(match_data, dict):
            return {"error": "Не удалось найти данные матча в ответе"}

        # 3. Парсинг данных
        
        # Победитель
        winner_team_id = None
        elo_info = match_data.get('calculateEloFrom')
        if isinstance(elo_info, dict):
            winner_team_id = elo_info.get('winner')

        # Поиск игрока
        target_player = None
        my_team_id = None
        
        teams = match_data.get('teams')
        if not isinstance(teams, list): teams = []

        for team in teams:
            if not isinstance(team, dict): continue
            
            players = team.get('players')
            if not isinstance(players, list): continue

            for player in players:
                if not isinstance(player, dict): continue
                
                p_nick = player.get('nickname', '')
                # Сравниваем строками в нижнем регистре
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
        score_info = match_data.get('i18', 'N/A')
        match_score = score_info
        if isinstance(score_info, dict):
            match_score = score_info.get('score', 'N/A')

        stats = {
            "nickname": target_player.get('nickname', target_nickname),
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
        # Возвращаем текст ошибки на фронтенд для диагностики
        return {"error": f"System Error: {str(e)}"}

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