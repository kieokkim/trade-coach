import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "tradecoach.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS weaknesses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT    NOT NULL,
                weakness    TEXT    NOT NULL,
                count       INTEGER DEFAULT 1,
                last_seen   DATE    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trade_history (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     TEXT    NOT NULL,
                date           DATE    NOT NULL,
                win_rate       FLOAT   NOT NULL,
                avg_rr         FLOAT   NOT NULL,
                max_drawdown   INTEGER,
                main_weakness  TEXT,
                trade_count    INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS quiz_results (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT    NOT NULL,
                concept      TEXT    NOT NULL,
                passed       BOOLEAN NOT NULL,
                retry_count  INTEGER DEFAULT 0,
                date         DATE    NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_weaknesses_session_tag
                ON weaknesses (session_id, weakness);

            CREATE INDEX IF NOT EXISTS idx_trade_history_session_date
                ON trade_history (session_id, date);

            CREATE INDEX IF NOT EXISTS idx_quiz_results_session_concept
                ON quiz_results (session_id, concept);
        """)
