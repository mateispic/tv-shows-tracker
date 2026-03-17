import sqlite3

conn = sqlite3.connect('tvshows.db')
cursor = conn.cursor()

# Enable foreign keys
cursor.execute("PRAGMA foreign_keys = ON;")

# ------------------ DELETE OLD DATA ------------------
cursor.execute("DROP TABLE IF EXISTS progress")
cursor.execute("DROP TABLE IF EXISTS episodes")
cursor.execute("DROP TABLE IF EXISTS seasons")
cursor.execute("DROP TABLE IF EXISTS show_genres")
cursor.execute("DROP TABLE IF EXISTS shows")
cursor.execute("DROP TABLE IF EXISTS genres")

# ------------------ CREATE TABLES ------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS shows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    release_year INTEGER NOT NULL,
    total_seasons INTEGER NOT NULL,
    imdb_rating REAL NOT NULL,
    imdb_link TEXT NOT NULL
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS show_genres (
    show_id INTEGER,
    genre_id INTEGER,
    PRIMARY KEY (show_id, genre_id),
    FOREIGN KEY (show_id) REFERENCES shows(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    show_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    release_year INTEGER NOT NULL,
    UNIQUE(show_id, season_number),
    FOREIGN KEY (show_id) REFERENCES shows(id) ON DELETE CASCADE
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    episode_number INTEGER NOT NULL,
    air_date TEXT NOT NULL,
    imdb_rating REAL NOT NULL,
    UNIQUE(season_id, episode_number),
    FOREIGN KEY (season_id) REFERENCES seasons(id) ON DELETE CASCADE
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    show_id INTEGER UNIQUE,
    seasons_watched INTEGER NOT NULL,
    finished BOOLEAN NOT NULL,
    personal_rating REAL,
    FOREIGN KEY (show_id) REFERENCES shows(id) ON DELETE CASCADE
);
""")

# ------------------ INSERT SAMPLE DATA ------------------

cursor.execute("""
INSERT INTO shows (title, release_year, total_seasons, imdb_rating, imdb_link)
VALUES ('Archive 81', 2022, 1, 7.3, 'https://www.imdb.com/title/tt13365348')
""")

cursor.execute("""
INSERT INTO shows (title, release_year, total_seasons, imdb_rating, imdb_link)
VALUES ('Lupin', 2021, 3, 7.5, 'https://www.imdb.com/title/tt2531336')
""")

cursor.execute("""
INSERT INTO shows (title, release_year, total_seasons, imdb_rating, imdb_link)
VALUES ('Space Force', 2020, 2, 6.7, 'https://www.imdb.com/title/tt9612516')
""")
space_force_id = cursor.lastrowid

# ------------------ Genres ------------------
cursor.execute("INSERT INTO genres (name) VALUES ('Drama')")
cursor.execute("INSERT INTO genres (name) VALUES ('Horror')")
cursor.execute("INSERT INTO genres (name) VALUES ('Sci-Fi')")
cursor.execute("INSERT INTO genres (name) VALUES ('Thriller')")
cursor.execute("INSERT INTO genres (name) VALUES ('Mystery')")
cursor.execute("INSERT INTO genres (name) VALUES ('Action')")
cursor.execute("INSERT INTO genres (name) VALUES ('Crime')")
cursor.execute("INSERT INTO genres (name) VALUES ('Sitcom')")
cursor.execute("INSERT INTO genres (name) VALUES ('Comedy')")

# ------------------ Shows_Genres ------------------
# Archive 81 - Drama, Horror, Sci-Fi, Thriller, Mystery
cursor.execute("INSERT INTO show_genres VALUES (1, 1)")
cursor.execute("INSERT INTO show_genres VALUES (1, 2)")
cursor.execute("INSERT INTO show_genres VALUES (1, 3)")
cursor.execute("INSERT INTO show_genres VALUES (1, 4)")
cursor.execute("INSERT INTO show_genres VALUES (1, 5)")

# Lupin - Action, Crime, Drama, Mystery
cursor.execute("INSERT INTO show_genres VALUES (2, 6)")
cursor.execute("INSERT INTO show_genres VALUES (2, 7)")
cursor.execute("INSERT INTO show_genres VALUES (2, 1)")
cursor.execute("INSERT INTO show_genres VALUES (2, 5)")

# Space Force - Sitcom, Comedy
cursor.execute("INSERT INTO show_genres VALUES (3, 8)")
cursor.execute("INSERT INTO show_genres VALUES (3, 9)")

# ------------------ Seasons ------------------
# Archive 81
cursor.execute("INSERT INTO seasons (show_id, season_number, release_year) VALUES (1, 1, 2022)")

# Lupin
cursor.execute("INSERT INTO seasons (show_id, season_number, release_year) VALUES (2, 1, 2021)")
cursor.execute("INSERT INTO seasons (show_id, season_number, release_year) VALUES (2, 2, 2021)")
cursor.execute("INSERT INTO seasons (show_id, season_number, release_year) VALUES (2, 3, 2023)")

# Space Force
cursor.execute("INSERT INTO seasons (show_id, season_number, release_year) VALUES (3, 1, 2020)")
cursor.execute("INSERT INTO seasons (show_id, season_number, release_year) VALUES (3, 2, 2022)")

# ------------------ Episodes ------------------
# Archive 81 - Season 1
cursor.execute("INSERT INTO episodes VALUES (NULL, 1, 'Mystery Signals', 1, '2022-01-14', 7.5)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 1, 'Wellspring', 2, '2022-01-14', 7.4)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 1, 'Terror in the Aisles', 3, '2022-01-14', 7.4)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 1, 'Spirit Receivers', 4, '2022-01-14', 7.9)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 1, 'Through the Looking Glass', 5, '2022-01-14', 7.6)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 1, 'The Circle', 6, '2022-01-14', 7.6)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 1, 'The Ferryman', 7, '2022-01-14', 7.3)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 1, 'What Lies Beneath', 8, '2022-01-14', 7.2)")

# Lupin - Season 1
cursor.execute("INSERT INTO episodes VALUES (NULL, 2, 'Chapter 1', 1, '2021-01-08', 7.9)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 2, 'Chapter 2', 2, '2021-01-08', 7.7)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 2, 'Chapter 3', 3, '2021-01-08', 7.6)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 2, 'Chapter 4', 4, '2021-01-08', 7.6)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 2, 'Chapter 5', 5, '2021-01-08', 7.7)")

# Lupin - Season 2
cursor.execute("INSERT INTO episodes VALUES (NULL, 3, 'Chapter 6', 1, '2021-06-11', 7.2)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 3, 'Chapter 7', 2, '2021-06-11', 7.3)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 3, 'Chapter 8', 3, '2021-06-11', 7.4)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 3, 'Chapter 9', 4, '2021-06-11', 7.8)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 3, 'Chapter 10', 5, '2021-06-11', 8.1)")

# Lupin - Season 3
cursor.execute("INSERT INTO episodes VALUES (NULL, 4, 'Chapter 1', 1, '2023-10-5', 7.8)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 4, 'Chapter 2', 2, '2023-10-5', 7.5)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 4, 'Chapter 3', 3, '2023-10-5', 7.4)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 4, 'Chapter 4', 4, '2023-10-5', 7.4)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 4, 'Chapter 5', 5, '2023-10-5', 7.7)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 4, 'Chapter 6', 6, '2023-10-5', 7.5)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 4, 'Chapter 7', 7, '2023-10-5', 7.9)")

# Space Force - Season 1
cursor.execute("INSERT INTO episodes VALUES (NULL, 5, 'The Launch', 1, '2022-05-29', 6.8)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 5, 'Save Epsilon 6!', 2, '2022-05-29', 7.3)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 5, 'Mark and Mallory Go to Washington', 3, '2022-05-29', 7.2)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 5, 'Lunar Habitat', 4, '2022-05-29', 6.9)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 5, 'Space Flag', 5, '2022-05-29', 6.7)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 5, 'The Spy', 6, '2022-05-29', 7.0)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 5, 'Edison Jaymes', 7, '2022-05-29', 6.9)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 5, 'Conjugal Visit', 8, '2022-05-29', 6.9)")
cursor.execute(
    "INSERT INTO episodes (id, season_id, title, episode_number, air_date, imdb_rating) VALUES (NULL, ?, ?, ?, ?, ?)",
    (5, "It's Good to Be Back on the Moon", 9, '2022-05-29', 7.5)
)
cursor.execute("INSERT INTO episodes VALUES (NULL, 5, 'Proportionate Response', 10, '2022-05-29', 7.1)")

# Space Force - Season 2
cursor.execute("INSERT INTO episodes VALUES (NULL, 6, 'The Inquiry', 1, '2022-02-18', 6.9)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 6, 'Budget Cuts', 2, '2022-02-18', 6.6)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 6, 'The Chinese Delegation', 3, '2022-02-18', 7.2)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 6, 'The Europa Project', 4, '2022-02-18', 6.7)")
cursor.execute("INSERT INTO episodes VALUES (NULL, 6, 'Mad (Buff) Confidence', 5, '2022-02-18', 6.8)")
cursor.execute(
    "INSERT INTO episodes (id, season_id, title, episode_number, air_date, imdb_rating) VALUES (NULL, ?, ?, ?, ?, ?)",
    (6, "The Doctor's Appointment", 6, '2022-02-18', 6.8)
)
cursor.execute("INSERT INTO episodes VALUES (NULL, 6, 'The Hack', 7, '2022-02-18', 7.2)")

# ------------------ Progress ------------------
cursor.execute("INSERT INTO progress (show_id, seasons_watched, finished, personal_rating) VALUES (1, 1, 1, 10)")
cursor.execute("INSERT INTO progress (show_id, seasons_watched, finished, personal_rating) VALUES (2, 1, 0, NULL)")
cursor.execute("INSERT INTO progress (show_id, seasons_watched, finished, personal_rating) VALUES (3, 0, 0, NULL)")

# Save
conn.commit()
conn.close()

print("Database created and populated successfully!")