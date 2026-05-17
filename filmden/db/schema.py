"""
filmden/db/schema.py
--------------------
Database initialization and helper functions for the 3-tier Filmden pipeline.
Tables: playlists → videos → movies
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "movies_db.sqlite")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS playlists (
            playlist_id TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            genre       TEXT,
            video_count INTEGER DEFAULT 0,
            status      TEXT DEFAULT 'pending',
            synced_at   TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS videos (
            video_id         TEXT PRIMARY KEY,
            playlist_id      TEXT NOT NULL,
            title            TEXT NOT NULL,
            genre            TEXT,
            status           TEXT DEFAULT 'pending',
            movies_extracted INTEGER DEFAULT 0,
            added_at         TEXT DEFAULT (datetime('now')),
            processed_at     TEXT,
            FOREIGN KEY (playlist_id) REFERENCES playlists(playlist_id)
        );

        CREATE TABLE IF NOT EXISTS movies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id    TEXT NOT NULL,
            playlist_id TEXT NOT NULL,
            genre       TEXT,
            movie_name  TEXT NOT NULL,
            details     TEXT,
            status      TEXT DEFAULT 'pending',
            added_at    TEXT DEFAULT (datetime('now')),
            used_at     TEXT,
            FOREIGN KEY (video_id)    REFERENCES videos(video_id),
            FOREIGN KEY (playlist_id) REFERENCES playlists(playlist_id)
        );
    """)

    conn.commit()
    conn.close()


def now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


# ── Playlist helpers ──────────────────────────────────────────────────────────

def playlist_count() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM playlists").fetchone()[0]


def insert_playlist(playlist_id, title, genre, video_count=0):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO playlists (playlist_id, title, genre, video_count)
            VALUES (?, ?, ?, ?)
        """, (playlist_id, title, genre, video_count))
        conn.commit()


def get_genres_with_pending_movies() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT DISTINCT m.genre FROM movies m WHERE m.status = 'pending' AND m.genre IS NOT NULL
        """).fetchall()
        return [r["genre"] for r in rows]


def get_genres_with_pending_videos() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT DISTINCT v.genre FROM videos v WHERE v.status = 'pending' AND v.genre IS NOT NULL
        """).fetchall()
        return [r["genre"] for r in rows]


# ── Video helpers ─────────────────────────────────────────────────────────────

def insert_video(video_id, playlist_id, title, genre):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO videos (video_id, playlist_id, title, genre)
            VALUES (?, ?, ?, ?)
        """, (video_id, playlist_id, title, genre))
        conn.commit()


def get_pending_video(genre: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("""
            SELECT v.* FROM videos v
            JOIN playlists p ON p.playlist_id = v.playlist_id
            WHERE v.status = 'pending' AND v.genre = ?
            ORDER BY RANDOM() LIMIT 1
        """, (genre,)).fetchone()


def mark_video(video_id: str, status: str, movies_extracted: int = None):
    with get_conn() as conn:
        if movies_extracted is not None:
            conn.execute("""
                UPDATE videos SET status=?, movies_extracted=?, processed_at=?
                WHERE video_id=?
            """, (status, movies_extracted, now(), video_id))
        else:
            conn.execute("UPDATE videos SET status=? WHERE video_id=?", (status, video_id))
        conn.commit()


# ── Movie helpers ─────────────────────────────────────────────────────────────

def insert_movie(video_id, playlist_id, genre, movie_name, details):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO movies (video_id, playlist_id, genre, movie_name, details)
            VALUES (?, ?, ?, ?, ?)
        """, (video_id, playlist_id, genre, movie_name, details))
        conn.commit()


def get_pending_movie(genre: str = None) -> sqlite3.Row | None:
    with get_conn() as conn:
        if genre:
            return conn.execute("""
                SELECT * FROM movies WHERE status='pending' AND genre=?
                ORDER BY RANDOM() LIMIT 1
            """, (genre,)).fetchone()
        return conn.execute("""
            SELECT * FROM movies WHERE status='pending'
            ORDER BY RANDOM() LIMIT 1
        """).fetchone()


def mark_movie(movie_id: int, status: str):
    with get_conn() as conn:
        used = now() if status == "used" else None
        conn.execute(
            "UPDATE movies SET status=?, used_at=? WHERE id=?",
            (status, used, movie_id)
        )
        conn.commit()
