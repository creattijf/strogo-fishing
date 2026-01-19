from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

def check_is_fishing(faceit_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        if not faceit_url: return "error"
        if "faceit.com" not in faceit_url:
            faceit_url = f"https://www.faceit.com/ru/players/{faceit_url}"

        response = requests.get(faceit_url, headers=headers)
        if response.status_code != 200: return "error"

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Логика поиска
        room_link = soup.select_one('a[href*="/room/"]')
        text_check = soup.find(string="Playing now") or soup.find(string="Currently playing") or soup.find(string="LIVE")

        if room_link or text_check:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error: {e}")
        return "error"

# --- ГЛАВНЫЕ ИЗМЕНЕНИЯ ЗДЕСЬ ---

# 1. Добавляем корневой маршрут, чтобы при открытии прямой ссылки не было ошибки 404
@app.route('/', methods=['GET'])
def home():
    return "Сервер Strogo Fishing работает! Используй POST запрос на /api/check_fish"

# 2. Дублируем маршруты. Vercel иногда отрезает /api, иногда нет.
# Мы ловим оба варианта.
@app.route('/api/check_fish', methods=['POST', 'GET'])
@app.route('/check_fish', methods=['POST', 'GET']) 
def check_fish():
    # Если открыли в браузере (GET), покажем инструкцию
    if request.method == 'GET':
        return jsonify({"status": "info", "message": "Используй POST запрос с JSON данными"})

    # Обработка POST (как раньше)
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "Нет данных"})
        
    url = data.get('url')
    status = check_is_fishing(url)
    
    if status == "error":
        return jsonify({"status": "error", "message": "Ошибка доступа к Faceit"})
    elif status:
        return jsonify({"status": "online", "message": "В пруду 🎣"})
    else:
        return jsonify({"status": "offline", "message": "Не в пруду ❌"})

# Для локального запуска
if __name__ == '__main__':
    app.run(debug=True)