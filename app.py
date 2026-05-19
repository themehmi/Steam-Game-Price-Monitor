from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
from bs4 import BeautifulSoup
import re
import sqlite3
import threading
import time

app = Flask(__name__)
DB_NAME = "steam_tracker.db"

# DATABASE SETUP
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                app_id TEXT PRIMARY KEY,
                title TEXT,
                initial_price REAL,
                current_price REAL,
                initial_price_str TEXT,
                price_str TEXT,
                alert_type TEXT,
                threshold REAL,
                triggered INTEGER DEFAULT 0
            )
        ''')
        conn.commit()

init_db()

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
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT app_id, alert_type, threshold, triggered, initial_price FROM watchlist")
                games = cursor.fetchall()
                
                for app_id, alert_type, threshold, triggered, initial_price in games:
                    data = scrape_steam_price(app_id)
                    if data:
                        current_price = data['price_float']
                        price_str = data['price_str']
                        
                        is_triggered = 0
                        if alert_type == "target_price" and current_price <= threshold:
                            is_triggered = 1
                        elif alert_type == "discount_drop" and "discount" in price_str.lower():
                            is_triggered = 1
                            
                        if is_triggered == 1 and triggered == 0:
                            cursor.execute("UPDATE watchlist SET current_price=?, price_str=?, triggered=1 WHERE app_id=?", (current_price, price_str, app_id))
                        else:
                            cursor.execute("UPDATE watchlist SET current_price=?, price_str=? WHERE app_id=?", (current_price, price_str, app_id))
                conn.commit()
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
                        with sqlite3.connect(DB_NAME) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT OR REPLACE INTO watchlist (app_id, title, initial_price, current_price, initial_price_str, price_str, alert_type, threshold, triggered)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                            """, (app_id, data['title'], data['price_float'], data['price_float'], data['price_str'], data['price_str'], alert_type, threshold))
                            conn.commit()
                    except Exception as e:
                        error_msg = f"Database error: {e}"
                else:
                    error_msg = "Could not fetch game details. Check the App ID."

    # Handle Dashboard Search
    search_query = request.args.get('search', '').strip()
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        if search_query:
            cursor.execute("SELECT app_id, title, initial_price_str, price_str, alert_type, threshold, triggered, initial_price, current_price FROM watchlist WHERE title LIKE ?", ('%' + search_query + '%',))
        else:
            cursor.execute("SELECT app_id, title, initial_price_str, price_str, alert_type, threshold, triggered, initial_price, current_price FROM watchlist")
        watchlist = cursor.fetchall()

    return render_template('index.html', watchlist=watchlist, error=error_msg, search_query=search_query)

# NEW ROUTE: DELETE GAME
@app.route('/delete/<app_id>', methods=['POST'])
def delete_game(app_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watchlist WHERE app_id = ?", (app_id,))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/api/alerts')
def check_alerts():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT app_id, title, price_str FROM watchlist WHERE triggered = 1")
        alerts = cursor.fetchall()
    return jsonify([{"app_id": a[0], "title": a[1], "price": a[2]} for a in alerts])

@app.route('/api/dismiss', methods=['POST'])
def dismiss_alert():
    app_id = request.json.get('app_id')
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE watchlist SET triggered = 2 WHERE app_id = ?", (app_id,))
        conn.commit()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)