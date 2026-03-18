# TV Shows Tracker

This is a small Flask project where I can keep track of TV shows.
It has a simple web interface and also some REST API endpoints.
The data is stored in a SQLite database.

## What this project can do

- Show a list of TV shows
- Search shows by title
- Add a new show
- Edit an existing show
- Delete a show
- Access show, season, and episode data through API routes

## Technologies used

- Python
- Flask
- SQLite
- HTML/CSS (Jinja templates)

## Architecture

The project has a simple 3-layer architecture:

- Presentation layer: HTML pages from templates (shows list, add form, edit form, episodes page).
- Application layer: Flask routes split into blueprints:
    - api.py for REST API routes
    - web.py for web routes
    - run.py to create the Flask app and register both blueprints
- Data layer: SQLite database (tvshows.db) with relational tables.

Request flow:

1. User sends request from browser or Postman.
2. If request is from browser, web.py calls API endpoints using requests.
3. API route from api.py validates input and executes SQL on SQLite.
4. Response is returned as HTML page (web) or JSON (API).

## Project structure

```
tv-shows-tracker/
|-- run.py
|-- api.py
|-- web.py
|-- database.py
|-- requirements.txt
|-- tvshows.db
|-- static/
|   `-- style.css
`-- templates/
    |-- shows.html
    |-- add_show.html
    |-- edit_show.html
    `-- episodes.html
```

## Database structure

The database is initialized from database.py and contains these tables:

1. shows
- id (PK)
- title
- release_year
- total_seasons
- imdb_rating
- imdb_link

2. genres
- id (PK)
- name (unique)

3. show_genres
- show_id (FK -> shows.id)
- genre_id (FK -> genres.id)
- composite primary key (show_id, genre_id)

4. seasons
- id (PK)
- show_id (FK -> shows.id)
- season_number
- release_year
- unique(show_id, season_number)

5. episodes
- id (PK)
- season_id (FK -> seasons.id)
- title
- episode_number
- air_date
- imdb_rating
- unique(season_id, episode_number)

6. progress
- id (PK)
- show_id (FK -> shows.id, unique)
- seasons_watched
- finished
- personal_rating

Important relation summary:

- One show has many seasons.
- One season has many episodes.
- Shows and genres have many-to-many relation through show_genres.

## How to run

1. Open terminal in the project folder.
2. (Optional but recommended) Activate virtual environment:

```powershell
venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Create and populate the database:

```powershell
python database.py
```

5. Start the Flask app:

```powershell
python run.py
```

6. Open in browser:

```text
http://127.0.0.1:5000/shows
```

## Main web routes

- `GET /shows` - show all TV shows (+ search with `?q=...`)
- `GET /shows/add` - page to add a show
- `POST /shows/add` - save a new show
- `GET /shows/<id>/edit` - page to edit a show
- `POST /shows/<id>/edit` - save edited show
- `POST /shows/<id>/delete` - delete a show
- `GET /shows/<id>/episodes` - show all episodes for one show

## API endpoints

- `GET /api/shows`
- `GET /api/shows/<id>`
- `POST /api/shows`
- `PUT /api/shows/<id>`
- `PATCH /api/shows/<id>`
- `DELETE /api/shows/<id>`
- `GET /api/shows/<id>/seasons`
- `POST /api/shows/<id>/seasons`
- `GET /api/shows/<id>/episodes`
- `POST /api/seasons/<season_id>/episodes`

Common status codes used:

- 200: request successful
- 201: resource created
- 400: bad request / missing fields / duplicate data
- 404: resource not found

Extra API behavior:

- `GET /api/shows` also returns progress text for each show.
- `GET /api/shows/<id>` also includes progress fields (`seasons_watched`, `finished`, `personal_rating`).
- `POST /api/shows` can also receive progress fields when creating a show.

## Postman testing

I tested the API endpoints in Postman using GET, POST, PUT, PATCH, and DELETE requests.

Tested examples:

- GET all shows
- GET show by id
- POST create show
- PUT full update show
- PATCH partial update show
- DELETE show
- GET/POST seasons for show
- GET episodes for show
- POST episode for season

## Notes

- The `database.py` script drops and recreates tables, then inserts sample data.
- If you run `database.py` again, old data will be replaced.
- The web interface communicates with the API endpoints from the same Flask app.