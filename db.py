import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "tradecoach.db"

logger = logging.getLogger(__name__)


@contextmanager
def get_db():
    logger.info("get_db: opening connection to %s", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
        logger.info("get_db: commit ok")
    except Exception as e:
        logger.warning("get_db: rollback due to %s", e)
        conn.rollback()
        raise
    finally:
        conn.close()
        logger.info("get_db: connection closed")


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

            CREATE TABLE IF NOT EXISTS performance_snapshots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT    NOT NULL,
                period          TEXT,
                period_start    DATE,
                win_rate        FLOAT,
                avg_return_rate FLOAT,
                expected_value  FLOAT,
                loss_consistency FLOAT,
                profit_rate     FLOAT,
                top_weakness    TEXT,
                action_rule     TEXT
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_weaknesses_session_tag
                ON weaknesses (session_id, weakness);

            CREATE INDEX IF NOT EXISTS idx_trade_history_session_date
                ON trade_history (session_id, date);

            CREATE INDEX IF NOT EXISTS idx_quiz_results_session_concept
                ON quiz_results (session_id, concept);
        """)

        # trade_history 신규 KPI 컬럼 (마이그레이션)
        for col_ddl in [
            "ALTER TABLE trade_history ADD COLUMN avg_return_rate FLOAT",
            "ALTER TABLE trade_history ADD COLUMN expected_value  FLOAT",
            "ALTER TABLE trade_history ADD COLUMN loss_consistency FLOAT",
            "ALTER TABLE trade_history ADD COLUMN last_fetched_at TEXT",
        ]:
            try:
                conn.execute(col_ddl)
            except Exception:
                pass

        # weaknesses category 컬럼
        try:
            conn.execute("ALTER TABLE weaknesses ADD COLUMN category TEXT DEFAULT 'ict'")
        except Exception:
            pass
