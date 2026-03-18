from flask import Flask, request, jsonify, render_template, redirect
import requests
import sqlite3

app = Flask(__name__)
app.json.sort_keys = False
DB_PATH = 'tvshows.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def fetch_shows():
    conn = get_db_connection()
    shows = conn.execute("SELECT * FROM shows").fetchall()
    conn.close()
    return [dict(show) for show in shows]

# ========================================================

# ---------------- API ----------------

# ========================================================

# ---------------- GET: All shows ----------------
@app.route('/api/shows', methods=['GET'])
def get_shows():
    shows = fetch_shows()
    for show in shows:
        show["_links"] = {
            "self": f"/shows/{show['id']}",
            "seasons": f"/shows/{show['id']}/seasons",
            "episodes": f"/shows/{show['id']}/episodes"
        }
    return jsonify(shows), 200

# ---------------- GET: A show by id ----------------
@app.route('/api/shows/<int:show_id>', methods=['GET'])
def get_show(show_id):
    conn = get_db_connection()
    show = conn.execute("SELECT * FROM shows WHERE id = ?", (show_id,)).fetchone()
    conn.close()
    
    if show is None:
        return jsonify({"error": "Show not found"}), 404
    
    show_dict = dict(show)
    
    show_dict["_links"] = {
        "self": f"/shows/{show_id}",
        "seasons": f"/shows/{show_id}/seasons",
        "episodes": f"/shows/{show_id}/episodes",
        "update": f"/shows/{show_id}",
        "delete": f"/shows/{show_id}"
    }

    return jsonify(show_dict), 200

# ---------------- GET: All seasons for show by id ----------------
@app.route('/api/shows/<int:show_id>/seasons', methods=['GET'])
def get_seasons_for_show(show_id):
    conn = get_db_connection()

    show = conn.execute("SELECT * FROM shows WHERE id = ?", (show_id,)).fetchone()
    if show is None:
        conn.close()
        return jsonify({"error": "Show not found"}), 404

    seasons = conn.execute(
        "SELECT * FROM seasons WHERE show_id = ?",
        (show_id,)
    ).fetchall()

    conn.close()

    if not seasons:
        return jsonify({"error": "Seasons not found"}), 404

    return jsonify([dict(season) for season in seasons]), 200

# ---------------- GET: All episodes for show by id ----------------
@app.route('/api/shows/<int:show_id>/episodes', methods=['GET'])
def get_episodes_for_show(show_id):
    conn = get_db_connection()

    show = conn.execute(
        "SELECT * FROM shows WHERE id = ?",
        (show_id,)
    ).fetchone()

    if show is None:
        conn.close()
        return jsonify({"error": "Show not found"}), 404

    episodes = conn.execute(
        """
        SELECT e.*
        FROM episodes e
        JOIN seasons s ON e.season_id = s.id
        WHERE s.show_id = ?
        ORDER BY s.season_number, e.episode_number
        """,
        (show_id,)
    ).fetchall()

    conn.close()

    if not episodes:
        return jsonify({"error": "Episodes not found"}), 404

    return jsonify([dict(ep) for ep in episodes]), 200

# ---------------- POST: Add a show ----------------
@app.route('/api/shows', methods=['POST'])
def create_show():
    data = request.json

    required_fields = ['title', 'release_year', 'total_seasons', 'imdb_rating', 'imdb_link']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO shows (title, release_year, total_seasons, imdb_rating, imdb_link) VALUES (?, ?, ?, ?, ?)",
        (data['title'], data['release_year'], data['total_seasons'], data['imdb_rating'], data['imdb_link'])
    )
    conn.commit()
    show_id = cursor.lastrowid
    conn.close()

    return jsonify({"message": "Show created", "id": show_id}), 201

# ---------------- POST: Add season for a show by id ----------------
@app.route('/api/shows/<int:show_id>/seasons', methods=['POST'])
def create_season(show_id):
    data = request.json
    required_fields = ['season_number', 'release_year']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()

    show = conn.execute("SELECT * FROM shows WHERE id = ?", (show_id,)).fetchone()
    if show is None:
        conn.close()
        return jsonify({"error": "Show not found"}), 404

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO seasons (show_id, season_number, release_year) VALUES (?, ?, ?)",
            (show_id, data['season_number'], data['release_year'])
        )
        conn.commit()
        season_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Season already exists for this show"}), 400

    conn.close()
    return jsonify({"message": "Season created", "id": season_id}), 201

# ---------------- POST: Add an episode to a season of a show by id ----------------
@app.route('/api/seasons/<int:season_id>/episodes', methods=['POST'])
def create_episode(season_id):
    data = request.json
    required_fields = ['title', 'episode_number', 'air_date', 'imdb_rating']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()

    season = conn.execute("SELECT * FROM seasons WHERE id = ?", (season_id,)).fetchone()
    if season is None:
        conn.close()
        return jsonify({"error": "Season not found"}), 404

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO episodes (season_id, title, episode_number, air_date, imdb_rating) VALUES (?, ?, ?, ?, ?)",
            (season_id, data['title'], data['episode_number'], data['air_date'], data['imdb_rating'])
        )
        conn.commit()
        episode_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Episode already exists for this season"}), 400

    conn.close()
    return jsonify({"message": "Episode created", "id": episode_id}), 201

# ---------------- PUT: Update a show by id ----------------
@app.route('/api/shows/<int:show_id>', methods=['PUT'])
def update_show(show_id):
    data = request.json

    required_fields = ['title', 'release_year', 'total_seasons', 'imdb_rating', 'imdb_link']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()

    show = conn.execute("SELECT * FROM shows WHERE id = ?", (show_id,)).fetchone()
    if show is None:
        conn.close()
        return jsonify({"error": "Show not found"}), 404

    conn.execute(
        """UPDATE shows 
           SET title = ?, release_year = ?, total_seasons = ?, imdb_rating = ?, imdb_link = ?
           WHERE id = ?""",
        (data['title'], data['release_year'], data['total_seasons'],
         data['imdb_rating'], data['imdb_link'], show_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Show fully updated"}), 200

# ---------------- PATCH: Partially update a show by id ----------------
@app.route('/api/shows/<int:show_id>', methods=['PATCH'])
def patch_show(show_id):
    data = request.json
    
    if not data:
        return jsonify({"error": "No fields provided"}), 400

    conn = get_db_connection()
    
    show = conn.execute("SELECT * FROM shows WHERE id = ?", (show_id,)).fetchone()
    if show is None:
        conn.close()
        return jsonify({"error": "Show not found"}), 404

    fields = []
    values = []

    for key in data:
        fields.append(f"{key} = ?")
        values.append(data[key])

    values.append(show_id)

    query = f"UPDATE shows SET {', '.join(fields)} WHERE id = ?"

    conn.execute(query, values)
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Show partially updated"}), 200

# ---------------- DELETE: Remove a show by id ----------------
@app.route('/api/shows/<int:show_id>', methods=['DELETE'])
def delete_show(show_id):
    conn = get_db_connection()

    show = conn.execute(
        "SELECT * FROM shows WHERE id = ?",
        (show_id,)
    ).fetchone()

    if show is None:
        conn.close()
        return jsonify({"error": "Show not found"}), 404

    conn.execute(
        "DELETE FROM shows WHERE id = ?",
        (show_id,)
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Show deleted successfully"}), 200

# ========================================================

# ---------------- Web Client ----------------

# ========================================================

@app.route('/shows')
def shows_view():
    search_query = request.args.get('q', '').strip()

    resp = requests.get('http://localhost:5000/api/shows')
    if resp.status_code == 200:
        shows = resp.json()
        if search_query:
            shows = [show for show in shows if search_query.lower() in show['title'].lower()]
    else:
        shows = []

    no_results = len(shows) == 0
    return render_template('shows.html', shows=shows, search_query=search_query, no_results=no_results)

@app.route('/shows/add', methods=['GET', 'POST'])
def add_show():
    if request.method == 'POST':
        data = request.form

        required_fields = ['title', 'release_year', 'total_seasons', 'imdb_rating', 'imdb_link']
        if not all(field in data and data[field].strip() for field in required_fields):
            return "Missing required fields", 400

        payload = {
            "title": data['title'],
            "release_year": int(data['release_year']),
            "total_seasons": int(data['total_seasons']),
            "imdb_rating": float(data['imdb_rating']),
            "imdb_link": data['imdb_link']
        }

        response = requests.post('http://127.0.0.1:5000/api/shows', json=payload)

        if response.status_code == 201:
            return redirect('/shows')
        else:
            return f"Error creating show: {response.json().get('error', 'Unknown error')}", 400

    return render_template('add_show.html')

@app.route('/shows/<int:show_id>/edit', methods=['GET', 'POST'])
def edit_show(show_id):
    api_url = f'http://127.0.0.1:5000/api/shows/{show_id}'

    if request.method == 'POST':
        data = {
            "title": request.form['title'],
            "release_year": int(request.form['release_year']),
            "total_seasons": int(request.form['total_seasons']),
            "imdb_rating": float(request.form['imdb_rating']),
            "imdb_link": request.form['imdb_link']
        }
        response = requests.patch(api_url, json=data)
        if response.status_code == 200:
            return redirect('/shows')
        else:
            return f"Error updating show: {response.text}", response.status_code

    response = requests.get(api_url)
    if response.status_code != 200:
        return "Show not found", 404

    show = response.json()
    return render_template('edit_show.html', show=show)

@app.route("/shows/<int:show_id>/delete", methods=["POST"])
def delete_show_web(show_id):
    api_url = f'http://127.0.0.1:5000/api/shows/{show_id}'
    response = requests.delete(api_url)

    if response.status_code == 200:
        return redirect('/shows')
    else:
        return f"Error deleting show: {response.json().get('error', 'Unknown error')}", response.status_code

if __name__ == '__main__':
    app.run(debug=True)
