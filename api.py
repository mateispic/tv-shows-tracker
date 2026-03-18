from flask import Blueprint, request, jsonify, url_for
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


def parse_genre_ids(raw_genre_ids):
    if raw_genre_ids is None:
        return None
    if not isinstance(raw_genre_ids, list):
        raise ValueError("genre_ids must be a list")

    parsed = []
    for genre_id in raw_genre_ids:
        parsed.append(int(genre_id))

    # Remove duplicates while keeping order.
    return list(dict.fromkeys(parsed))


def validate_genre_ids(conn, genre_ids):
    if not genre_ids:
        return True

    placeholders = ",".join("?" for _ in genre_ids)
    rows = conn.execute(
        f"SELECT id FROM genres WHERE id IN ({placeholders})",
        genre_ids
    ).fetchall()
    return len(rows) == len(genre_ids)


def set_show_genres(conn, show_id, genre_ids):
    conn.execute("DELETE FROM show_genres WHERE show_id = ?", (show_id,))

    if not genre_ids:
        return

    conn.executemany(
        "INSERT INTO show_genres (show_id, genre_id) VALUES (?, ?)",
        [(show_id, genre_id) for genre_id in genre_ids]
    )


def with_self_link(response, endpoint, **values):
    self_url = url_for(endpoint, _external=False, **values)
    response.headers["Link"] = f'<{self_url}>; rel="self"'
    return response

# ---------------- GET: All shows ----------------
@api_bp.route('/api/shows', methods=['GET'])
def get_shows():
    conn = get_db_connection()
    
    shows = conn.execute("SELECT * FROM shows").fetchall()
    shows_list = []

    for show in shows:
        show_dict = dict(show)
        show_dict["_links"] = {
            "self": f"/api/shows/{show_dict['id']}",
            "collection": "/api/shows",
            "seasons": f"/api/shows/{show_dict['id']}/seasons",
            "episodes": f"/api/shows/{show_dict['id']}/episodes",
            "imdb": show_dict['imdb_link']
        }

        progress = conn.execute(
            "SELECT seasons_watched, finished, personal_rating FROM progress WHERE show_id = ?",
            (show_dict['id'],)
        ).fetchone()

        genres = conn.execute(
            """
            SELECT g.name
            FROM genres g
            JOIN show_genres sg ON sg.genre_id = g.id
            WHERE sg.show_id = ?
            ORDER BY g.name
            """,
            (show_dict['id'],)
        ).fetchall()

        show_dict['genres'] = [row['name'] for row in genres]
        show_dict['genres_text'] = ", ".join(show_dict['genres']) if show_dict['genres'] else "No genres"

        if progress:
            progress_dict = dict(progress)
            seasons_watched = progress_dict['seasons_watched']
            finished = bool(progress_dict['finished'])
            rating = progress_dict.get('personal_rating')

            progress_text = f"{seasons_watched}/{show_dict['total_seasons']} seasons watched"
            if finished:
                progress_text += " (finished)"
            if rating is not None:
                progress_text += f" | Rating: {rating}/10"
            show_dict['progress_text'] = progress_text
        else:
            show_dict['progress_text'] = f"0/{show_dict['total_seasons']} seasons watched"

        shows_list.append(show_dict)

    conn.close()
    response = jsonify(shows_list)
    response.status_code = 200
    return with_self_link(response, 'api.get_shows')

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

    genres = conn.execute(
        """
        SELECT g.id, g.name
        FROM genres g
        JOIN show_genres sg ON sg.genre_id = g.id
        WHERE sg.show_id = ?
        ORDER BY g.name
        """,
        (show_id,)
    ).fetchall()

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

    show_dict["genre_ids"] = [genre["id"] for genre in genres]
    show_dict["genres"] = [genre["name"] for genre in genres]

    show_dict["_links"] = {
        "self": f"/api/shows/{show_id}",
        "collection": "/api/shows",
        "seasons": f"/api/shows/{show_id}/seasons",
        "episodes": f"/api/shows/{show_id}/episodes",
        "update": f"/api/shows/{show_id}",
        "delete": f"/api/shows/{show_id}"
    }

    response = jsonify(show_dict)
    response.status_code = 200
    return with_self_link(response, 'api.get_show', show_id=show_id)


# ---------------- GET: All genres ----------------
@api_bp.route('/api/genres', methods=['GET'])
def get_genres():
    conn = get_db_connection()
    genres = conn.execute("SELECT id, name FROM genres ORDER BY name").fetchall()
    conn.close()

    genres_list = []
    for genre in genres:
        genre_dict = dict(genre)
        genre_dict["_links"] = {
            "self": f"/api/genres/{genre_dict['id']}",
            "collection": "/api/genres",
            "shows": f"/api/shows?genre_id={genre_dict['id']}"
        }
        genres_list.append(genre_dict)

    response = jsonify(genres_list)
    response.status_code = 200
    return with_self_link(response, 'api.get_genres')

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

    seasons_list = []
    for season in seasons:
        season_dict = dict(season)
        season_dict["_links"] = {
            "self": f"/api/shows/{show_id}/seasons",
            "show": f"/api/shows/{show_id}",
            "episodes": f"/api/shows/{show_id}/episodes"
        }
        seasons_list.append(season_dict)

    response = jsonify(seasons_list)
    response.status_code = 200
    return with_self_link(response, 'api.get_seasons_for_show', show_id=show_id)

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

    episodes_list = []
    for episode in episodes:
        episode_dict = dict(episode)
        episode_dict["_links"] = {
            "self": f"/api/shows/{show_id}/episodes",
            "show": f"/api/shows/{show_id}"
        }
        episodes_list.append(episode_dict)

    response = jsonify(episodes_list)
    response.status_code = 200
    return with_self_link(response, 'api.get_episodes_for_show', show_id=show_id)

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

    try:
        genre_ids = parse_genre_ids(data.get('genre_ids', []))
    except (TypeError, ValueError):
        return jsonify({"error": "genre_ids must be a list of integers"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    if not validate_genre_ids(conn, genre_ids):
        conn.close()
        return jsonify({"error": "One or more genres are invalid"}), 400

    cursor.execute(
        "INSERT INTO shows (title, release_year, total_seasons, imdb_rating, imdb_link) VALUES (?, ?, ?, ?, ?)",
        (data['title'], data['release_year'], data['total_seasons'], data['imdb_rating'], data['imdb_link'])
    )
    show_id = cursor.lastrowid

    cursor.execute(
        "INSERT INTO progress (show_id, seasons_watched, finished, personal_rating) VALUES (?, ?, ?, ?)",
        (show_id, seasons_watched, finished, personal_rating)
    )

    set_show_genres(conn, show_id, genre_ids)

    conn.commit()
    conn.close()

    response = jsonify({
        "message": "Show created",
        "id": show_id,
        "_links": {
            "self": f"/api/shows/{show_id}",
            "collection": "/api/shows",
            "seasons": f"/api/shows/{show_id}/seasons",
            "episodes": f"/api/shows/{show_id}/episodes"
        }
    })
    response.status_code = 201
    response.headers["Location"] = f"/api/shows/{show_id}"
    return with_self_link(response, 'api.create_show')

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
    response = jsonify({
        "message": "Season created",
        "id": season_id,
        "_links": {
            "self": f"/api/shows/{show_id}/seasons",
            "show": f"/api/shows/{show_id}",
            "episodes": f"/api/shows/{show_id}/episodes"
        }
    })
    response.status_code = 201
    return with_self_link(response, 'api.create_season', show_id=show_id)

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

    show_row = conn.execute(
        "SELECT show_id FROM seasons WHERE id = ?",
        (season_id,)
    ).fetchone()

    conn.close()
    show_id = show_row["show_id"] if show_row else None

    response = jsonify({
        "message": "Episode created",
        "id": episode_id,
        "_links": {
            "self": f"/api/seasons/{season_id}/episodes",
            "season": f"/api/shows/{show_id}/seasons" if show_id else None,
            "show": f"/api/shows/{show_id}" if show_id else None,
            "episodes": f"/api/shows/{show_id}/episodes" if show_id else None
        }
    })
    response.status_code = 201
    return with_self_link(response, 'api.create_episode', season_id=season_id)

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

    try:
        genre_ids = parse_genre_ids(data.get('genre_ids'))
    except (TypeError, ValueError):
        conn.close()
        return jsonify({"error": "genre_ids must be a list of integers"}), 400

    if genre_ids is not None:
        if not validate_genre_ids(conn, genre_ids):
            conn.close()
            return jsonify({"error": "One or more genres are invalid"}), 400
        set_show_genres(conn, show_id, genre_ids)

    upsert_progress(conn, show_id, seasons_watched, finished, personal_rating)

    conn.commit()
    conn.close()

    response = jsonify({
        "message": "Show fully updated",
        "_links": {
            "self": f"/api/shows/{show_id}",
            "collection": "/api/shows",
            "seasons": f"/api/shows/{show_id}/seasons",
            "episodes": f"/api/shows/{show_id}/episodes"
        }
    })
    response.status_code = 200
    return with_self_link(response, 'api.update_show', show_id=show_id)

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
    extra_fields = {'genre_ids'}
    all_allowed = allowed_show_fields | allowed_progress_fields | extra_fields

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

    if 'genre_ids' in data:
        try:
            genre_ids = parse_genre_ids(data.get('genre_ids'))
        except (TypeError, ValueError):
            conn.close()
            return jsonify({"error": "genre_ids must be a list of integers"}), 400

        if not validate_genre_ids(conn, genre_ids):
            conn.close()
            return jsonify({"error": "One or more genres are invalid"}), 400

        set_show_genres(conn, show_id, genre_ids)

    conn.commit()
    conn.close()

    response = jsonify({
        "message": "Show partially updated",
        "_links": {
            "self": f"/api/shows/{show_id}",
            "collection": "/api/shows",
            "seasons": f"/api/shows/{show_id}/seasons",
            "episodes": f"/api/shows/{show_id}/episodes"
        }
    })
    response.status_code = 200
    return with_self_link(response, 'api.patch_show', show_id=show_id)

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

    response = jsonify({
        "message": "Show deleted successfully",
        "_links": {
            "self": f"/api/shows/{show_id}",
            "collection": "/api/shows",
            "create": "/api/shows"
        }
    })
    response.status_code = 200
    return with_self_link(response, 'api.delete_show', show_id=show_id)