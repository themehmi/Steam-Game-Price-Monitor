from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
from bs4 import BeautifulSoup
import re
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import threading
import time

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

# DATABASE SETUP
MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["steam_tracker"]
watchlist_col = db["watchlist"]

# STEAM SEARCH BY NAME HELPER
def get_app_id_from_name(game_name):
    """Searches Steam for a game name and returns its App ID"""
    search_url = f"https://store.steampowered.com/api/storesearch/?term={game_name}&l=english&cc=US"
    try:
        response = requests.get(search_url, timeout=5)
        data = response.json()
        if data.get('total', 0) > 0:
            # Return the exact App ID of the top search result
            return str(data['items'][0]['id'])
    except Exception:
        pass
    return None

# STEAM SCRAPER FUNCTION
def scrape_steam_price(app_id):
    url = f"https://store.steampowered.com/app/{app_id}/"
    cookies = {'birthtime': '283993201', 'lastagecheckage': '1-January-1979'}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    try:
        response = requests.get(url, cookies=cookies, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        title_element = soup.find('div', id='appHubAppName')
        game_title = title_element.text.strip() if title_element else f"App ID: {app_id}"

        price_element = soup.find('div', class_='discount_final_price') or soup.find('div', class_='game_purchase_price')

        if price_element:
            raw_price = price_element.text.strip()
            numeric_parts = re.findall(r'\d+\.?\d*', raw_price.replace(',', '.'))
            if numeric_parts:
                return {"title": game_title, "price_str": raw_price, "price_float": float(numeric_parts[-1])}
            elif "free" in raw_price.lower():
                return {"title": game_title, "price_str": "Free to Play", "price_float": 0.0}
        return None
    except Exception:
        return None

# BACKGROUND AUTO-UPDATER THREAD
def background_price_checker():
    while True:
        time.sleep(60) 
        try:
            games = list(watchlist_col.find({}, {"_id": 1, "alert_type": 1, "threshold": 1, "triggered": 1, "initial_price": 1}))
            for game in games:
                app_id = game["_id"]
                alert_type = game.get("alert_type")
                threshold = game.get("threshold", 0.0)
                triggered = game.get("triggered", 0)
                
                data = scrape_steam_price(app_id)
                if data:
                    current_price = data['price_float']
                    price_str = data['price_str']
                    
                    is_triggered = 0
                    if alert_type == "target_price" and current_price <= threshold:
                        is_triggered = 1
                    elif alert_type == "discount_drop" and "discount" in price_str.lower():
                        is_triggered = 1
                        
                    update_fields = {
                        "current_price": current_price,
                        "price_str": price_str
                    }
                    if is_triggered == 1 and triggered == 0:
                        update_fields["triggered"] = 1
                        
                    watchlist_col.update_one({"_id": app_id}, {"$set": update_fields})
        except Exception as e:
            print(f"Background worker error: {e}")

threading.Thread(target=background_price_checker, daemon=True).start()

# ROUTES
@app.route('/', methods=['GET', 'POST'])
def index():
    error_msg = None
    
    if request.method == 'POST':
        user_input = request.form.get('app_id', '').strip()
        alert_type = request.form.get('alert_type')
        try:
            threshold = float(request.form.get('threshold', 0))
        except ValueError:
            threshold = 0.0

        if user_input:
            # Check if input is a Name or an ID
            if user_input.isdigit():
                app_id = user_input
            else:
                app_id = get_app_id_from_name(user_input)
                
            if not app_id:
                error_msg = f"Could not find a Steam game matching '{user_input}'. Try using the exact App ID."
            else:
                data = scrape_steam_price(app_id)
                if data:
                    try:
                        watchlist_col.replace_one(
                            {"_id": app_id},
                            {
                                "_id": app_id,
                                "app_id": app_id,
                                "title": data['title'],
                                "initial_price": data['price_float'],
                                "current_price": data['price_float'],
                                "initial_price_str": data['price_str'],
                                "price_str": data['price_str'],
                                "alert_type": alert_type,
                                "threshold": threshold,
                                "triggered": 0
                            },
                            upsert=True
                        )
                    except Exception as e:
                        error_msg = f"Database error: {e}"
                else:
                    error_msg = "Could not fetch game details. Check the App ID."

    # Handle Dashboard Search
    search_query = request.args.get('search', '').strip()
    try:
        if search_query:
            cursor = watchlist_col.find({"title": {"$regex": re.escape(search_query), "$options": "i"}})
        else:
            cursor = watchlist_col.find()
        
        watchlist = []
        for doc in cursor:
            watchlist.append((
                doc.get("_id"),
                doc.get("title", ""),
                doc.get("initial_price_str", ""),
                doc.get("price_str", ""),
                doc.get("alert_type", ""),
                doc.get("threshold", 0.0),
                doc.get("triggered", 0),
                doc.get("initial_price", 0.0),
                doc.get("current_price", 0.0)
            ))
    except Exception as e:
        watchlist = []
        error_msg = f"Database error: {e}"

    return render_template('index.html', watchlist=watchlist, error=error_msg, search_query=search_query)

# NEW ROUTE: DELETE GAME
@app.route('/delete/<app_id>', methods=['POST'])
def delete_game(app_id):
    watchlist_col.delete_one({"_id": app_id})
    return redirect(url_for('index'))

@app.route('/api/alerts')
def check_alerts():
    alerts = []
    try:
        cursor = watchlist_col.find({"triggered": 1}, {"_id": 1, "title": 1, "price_str": 1})
        for doc in cursor:
            alerts.append({
                "app_id": doc.get("_id"),
                "title": doc.get("title", ""),
                "price": doc.get("price_str", "")
            })
    except Exception:
        pass
    return jsonify(alerts)

@app.route('/api/dismiss', methods=['POST'])
def dismiss_alert():
    app_id = request.json.get('app_id')
    watchlist_col.update_one({"_id": app_id}, {"$set": {"triggered": 2}})
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)
