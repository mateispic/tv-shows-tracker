from flask import Blueprint, render_template, request, redirect
import requests

web_bp = Blueprint('web', __name__)

@web_bp.route('/shows')
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

@web_bp.route('/shows/add', methods=['GET', 'POST'])
def add_show():
    if request.method == 'POST':
        data = request.form

        required_fields = ['title', 'release_year', 'total_seasons', 'imdb_rating', 'imdb_link']
        if not all(field in data and data[field].strip() for field in required_fields):
            return "Missing required fields", 400

        seasons_watched = int(data.get('seasons_watched', 0))
        personal_rating = float(data['personal_rating']) if data.get('personal_rating') else None
        total_seasons = int(data['total_seasons'])

        finished = seasons_watched >= total_seasons

        payload = {
            "title": data['title'],
            "release_year": int(data['release_year']),
            "total_seasons": total_seasons,
            "imdb_rating": float(data['imdb_rating']),
            "imdb_link": data['imdb_link'],
            "seasons_watched": seasons_watched,
            "finished": finished,
            "personal_rating": personal_rating
        }

        response = requests.post('http://127.0.0.1:5000/api/shows', json=payload)

        if response.status_code == 201:
            return redirect('/shows')
        else:
            return f"Error creating show: {response.json().get('error', 'Unknown error')}", 400

    return render_template('add_show.html')

@web_bp.route('/shows/<int:show_id>/edit', methods=['GET', 'POST'])
def edit_show(show_id):
    api_url = f'http://127.0.0.1:5000/api/shows/{show_id}'

    if request.method == 'POST':
        seasons_watched = int(request.form.get('seasons_watched', 0))
        personal_rating = float(request.form['personal_rating']) if request.form.get('personal_rating') else None
        total_seasons = int(request.form['total_seasons'])

        finished = seasons_watched >= total_seasons

        data = {
            "title": request.form['title'],
            "release_year": int(request.form['release_year']),
            "total_seasons": total_seasons,
            "imdb_rating": float(request.form['imdb_rating']),
            "imdb_link": request.form['imdb_link'],
            "seasons_watched": seasons_watched,
            "finished": finished,
            "personal_rating": personal_rating
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

@web_bp.route("/shows/<int:show_id>/delete", methods=["POST"])
def delete_show_web(show_id):
    api_url = f'http://127.0.0.1:5000/api/shows/{show_id}'
    response = requests.delete(api_url)

    if response.status_code == 200:
        return redirect('/shows')
    else:
        return f"Error deleting show: {response.json().get('error', 'Unknown error')}", response.status_code

@web_bp.route('/shows/<int:show_id>/episodes')
def episodes_view(show_id):
    response = requests.get(f'http://127.0.0.1:5000/api/shows/{show_id}')
    if response.status_code != 200:
        return "Show not found", 404

    show = response.json()
    show_title = show['title']

    response_episodes = requests.get(f'http://127.0.0.1:5000/api/shows/{show_id}/episodes')
    if response_episodes.status_code == 200:
        episodes = response_episodes.json()
    else:
        episodes = []

    return render_template('episodes.html', episodes=episodes, show_title=show_title)