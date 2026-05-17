import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger("filmden.db.trakt_schema")

DB_PATH = Path("filmden/movies_db.sqlite")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates the posted_movies tracking table if it doesn't exist."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posted_movies (
                tmdb_id   INTEGER PRIMARY KEY,
                title     TEXT,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    logger.info("Database initialized.")


def get_posted_ids() -> set:
    """Returns a set of all tmdb_ids that have already been posted."""
    with get_conn() as conn:
        rows = conn.execute("SELECT tmdb_id FROM posted_movies").fetchall()
    return {row["tmdb_id"] for row in rows}


def log_posted_movie(tmdb_id: int, title: str):
    """Inserts a movie into the posted_movies table to prevent future duplication."""
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO posted_movies (tmdb_id, title) VALUES (?, ?)",
            (tmdb_id, title),
        )
        conn.commit()
    logger.info("Logged posted movie: %s (tmdb_id=%s)", title, tmdb_id)
