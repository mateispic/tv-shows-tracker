from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)
app.json.sort_keys = False
DB_PATH = 'tvshows.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# ---------------- GET all shows ----------------
@app.route('/shows', methods=['GET'])
def get_shows():
    conn = get_db_connection()
    shows = conn.execute("SELECT * FROM shows").fetchall()
    conn.close()
    return jsonify([dict(show) for show in shows]), 200

# ---------------- GET show by id ----------------
@app.route('/shows/<int:show_id>', methods=['GET'])
def get_show(show_id):
    conn = get_db_connection()
    show = conn.execute("SELECT * FROM shows WHERE id = ?", (show_id,)).fetchone()
    conn.close()
    
    if show is None:
        return jsonify({"error": "Show not found"}), 404
    
    return jsonify(dict(show)), 200

# ---------------- GET seasons for show by id ----------------
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

# ---------------- GET all episodes for show by id ----------------
@app.route('/shows/<int:show_id>/episodes', methods=['GET'])
def get_episodes_for_show(show_id):
    conn = get_db_connection()

    # verificăm dacă show-ul există
    show = conn.execute(
        "SELECT * FROM shows WHERE id = ?",
        (show_id,)
    ).fetchone()

    if show is None:
        conn.close()
        return jsonify({"error": "Show not found"}), 404

    # preluăm toate episoadele pentru show-ul respectiv
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

if __name__ == '__main__':
    app.run(debug=True)
