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

## Project structure

```
tv-shows-tracker/
|-- app.py
|-- database.py
|-- requirements.txt
|-- tvshows.db
|-- static/
|   `-- style.css
`-- templates/
    |-- shows.html
    |-- add_show.html
    `-- edit_show.html
```

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
python app.py
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

## Main API routes

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

## Notes

- The `database.py` script drops and recreates tables, then inserts sample data.
- If you run `database.py` again, old data will be replaced.