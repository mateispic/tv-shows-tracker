from flask import Flask, request, jsonify, render_template
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
@app.route('/shows/<int:show_id>', methods=['GET'])
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
@app.route('/shows/<int:show_id>/seasons', methods=['GET'])
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
@app.route('/shows/<int:show_id>/episodes', methods=['GET'])
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
@app.route('/shows', methods=['POST'])
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
@app.route('/shows/<int:show_id>/seasons', methods=['POST'])
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
@app.route('/seasons/<int:season_id>/episodes', methods=['POST'])
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
@app.route('/shows/<int:show_id>', methods=['PUT'])
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
@app.route('/shows/<int:show_id>', methods=['PATCH'])
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
@app.route('/shows/<int:show_id>', methods=['DELETE'])
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

@app.route('/shows')
def shows_view():
    shows = fetch_shows()
    return render_template('shows.html', shows=shows)

if __name__ == '__main__':
    app.run(debug=True)
