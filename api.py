from flask import Blueprint, request, jsonify
import sqlite3

api_bp = Blueprint('api', __name__)

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


def upsert_progress(conn, show_id, seasons_watched, finished, personal_rating):
    conn.execute(
        """
        INSERT INTO progress (show_id, seasons_watched, finished, personal_rating)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(show_id) DO UPDATE SET
            seasons_watched = excluded.seasons_watched,
            finished = excluded.finished,
            personal_rating = excluded.personal_rating
        """,
        (show_id, seasons_watched, int(bool(finished)), personal_rating)
    )


# ---------------- GET: All shows ----------------
@api_bp.route('/api/shows', methods=['GET'])
def get_shows():
    shows = fetch_shows()
    conn = get_db_connection()

    for show in shows:
        show["_links"] = {
            "self": f"/shows/{show['id']}",
            "episodes": f"/shows/{show['id']}/episodes",
            "imdb": show['imdb_link']
        }

        progress = conn.execute(
            "SELECT seasons_watched, finished FROM progress WHERE show_id = ?",
            (show['id'],)
        ).fetchone()

        if progress:
            show['progress_text'] = f"{progress['seasons_watched']}/{show['total_seasons']} seasons watched"
            if progress['finished']:
                show['progress_text'] += " (finished)"
        else:
            show['progress_text'] = f"0/{show['total_seasons']} seasons watched"

    conn.close()
    return jsonify(shows), 200

# ---------------- GET: A show by id ----------------
@api_bp.route('/api/shows/<int:show_id>', methods=['GET'])
def get_show(show_id):
    conn = get_db_connection()
    show = conn.execute("SELECT * FROM shows WHERE id = ?", (show_id,)).fetchone()
    if show is None:
        conn.close()
        return jsonify({"error": "Show not found"}), 404
    
    # Preluam si progresul
    progress = conn.execute("SELECT * FROM progress WHERE show_id = ?", (show_id,)).fetchone()
    conn.close()
    
    show_dict = dict(show)
    if progress:
        show_dict.update({
            "seasons_watched": progress["seasons_watched"],
            "finished": bool(progress["finished"]),
            "personal_rating": progress["personal_rating"]
        })
    else:
        show_dict.update({
            "seasons_watched": 0,
            "finished": False,
            "personal_rating": None
        })

    show_dict["_links"] = {
        "self": f"/shows/{show_id}",
        "seasons": f"/shows/{show_id}/seasons",
        "episodes": f"/shows/{show_id}/episodes",
        "update": f"/shows/{show_id}",
        "delete": f"/shows/{show_id}"
    }

    return jsonify(show_dict), 200

# ---------------- GET: All seasons for show by id ----------------
@api_bp.route('/api/shows/<int:show_id>/seasons', methods=['GET'])
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
@api_bp.route('/api/shows/<int:show_id>/episodes', methods=['GET'])
def get_episodes_for_show(show_id):
    conn = get_db_connection()

    show = conn.execute(
        "SELECT * FROM shows WHERE id = ?", (show_id,)
    ).fetchone()

    if show is None:
        conn.close()
        return jsonify({"error": "Show not found"}), 404

    episodes = conn.execute(
        """
        SELECT e.id, e.title, e.episode_number, e.air_date, e.imdb_rating, s.season_number
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
@api_bp.route('/api/shows', methods=['POST'])
def create_show():
    data = request.json

    required_fields = ['title', 'release_year', 'total_seasons', 'imdb_rating', 'imdb_link']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    seasons_watched = data.get('seasons_watched', 0)
    finished = data.get('finished', False)
    personal_rating = data.get('personal_rating', None)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO shows (title, release_year, total_seasons, imdb_rating, imdb_link) VALUES (?, ?, ?, ?, ?)",
        (data['title'], data['release_year'], data['total_seasons'], data['imdb_rating'], data['imdb_link'])
    )
    show_id = cursor.lastrowid

    cursor.execute(
        "INSERT INTO progress (show_id, seasons_watched, finished, personal_rating) VALUES (?, ?, ?, ?)",
        (show_id, seasons_watched, finished, personal_rating)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Show created", "id": show_id}), 201

# ---------------- POST: Add season for a show by id ----------------
@api_bp.route('/api/shows/<int:show_id>/seasons', methods=['POST'])
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
@api_bp.route('/api/seasons/<int:season_id>/episodes', methods=['POST'])
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
@api_bp.route('/api/shows/<int:show_id>', methods=['PUT'])
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

    seasons_watched = data.get('seasons_watched', 0)
    finished = data.get('finished', seasons_watched >= data['total_seasons'])
    personal_rating = data.get('personal_rating', None)

    upsert_progress(conn, show_id, seasons_watched, finished, personal_rating)

    conn.commit()
    conn.close()

    return jsonify({"message": "Show fully updated"}), 200

# ---------------- PATCH: Partially update a show by id ----------------
@api_bp.route('/api/shows/<int:show_id>', methods=['PATCH'])
def patch_show(show_id):
    data = request.json
    
    if not data:
        return jsonify({"error": "No fields provided"}), 400

    conn = get_db_connection()
    
    show = conn.execute("SELECT * FROM shows WHERE id = ?", (show_id,)).fetchone()
    if show is None:
        conn.close()
        return jsonify({"error": "Show not found"}), 404

    allowed_show_fields = {'title', 'release_year', 'total_seasons', 'imdb_rating', 'imdb_link'}
    allowed_progress_fields = {'seasons_watched', 'finished', 'personal_rating'}
    all_allowed = allowed_show_fields | allowed_progress_fields

    invalid_fields = [key for key in data.keys() if key not in all_allowed]
    if invalid_fields:
        conn.close()
        return jsonify({"error": f"Invalid fields for update: {', '.join(invalid_fields)}"}), 400

    show_fields = []
    show_values = []
    for key in data:
        if key in allowed_show_fields:
            show_fields.append(f"{key} = ?")
            show_values.append(data[key])

    if show_fields:
        show_values.append(show_id)
        query = f"UPDATE shows SET {', '.join(show_fields)} WHERE id = ?"
        conn.execute(query, show_values)

    progress_needed = any(key in data for key in allowed_progress_fields) or 'total_seasons' in data
    if progress_needed:
        progress = conn.execute(
            "SELECT seasons_watched, finished, personal_rating FROM progress WHERE show_id = ?",
            (show_id,)
        ).fetchone()

        current_seasons_watched = progress['seasons_watched'] if progress else 0
        current_finished = bool(progress['finished']) if progress else False
        current_personal_rating = progress['personal_rating'] if progress else None

        new_total_seasons = data.get('total_seasons', show['total_seasons'])
        new_seasons_watched = data.get('seasons_watched', current_seasons_watched)
        new_personal_rating = data.get('personal_rating', current_personal_rating)

        if 'finished' in data:
            new_finished = data['finished']
        else:
            new_finished = new_seasons_watched >= new_total_seasons

        upsert_progress(conn, show_id, new_seasons_watched, new_finished, new_personal_rating)

    conn.commit()
    conn.close()
    
    return jsonify({"message": "Show partially updated"}), 200

# ---------------- DELETE: Remove a show by id ----------------
@api_bp.route('/api/shows/<int:show_id>', methods=['DELETE'])
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