from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

def check_is_fishing(faceit_url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        if "faceit.com" not in faceit_url:
            faceit_url = f"https://www.faceit.com/ru/players/{faceit_url}"

        response = requests.get(faceit_url, headers=headers)
        
        if response.status_code != 200:
            return "error"

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Поиск ссылки на комнату или текста о матче
        room_link = soup.select_one('a[href*="/room/"]')
        text_check = soup.find(string="Playing now") or soup.find(string="Currently playing")

        if room_link or text_check:
            return True
        else:
            return False
            
    except:
        return "error"

# Роут для API
@app.route('/api/check_fish', methods=['POST'])
def check_fish():
    data = request.json
    url = data.get('url')
    status = check_is_fishing(url)
    
    if status == "error":
        return jsonify({"status": "error", "message": "Ошибка"})
    elif status:
        return jsonify({"status": "online", "message": "В пруду 🎣"})
    else:
        return jsonify({"status": "offline", "message": "Не в пруду ❌"})

# app.run() НЕ НУЖЕН для Vercel