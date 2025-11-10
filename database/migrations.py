"""Database migrations for NHL Automation System."""
import sqlite3
from config.config import DATABASE_PATH


def run_migrations(db_path: str = DATABASE_PATH):
    """Run all database migrations."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")

    # Migration 1: Create game_stats table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_pk INTEGER UNIQUE NOT NULL,
            game_date TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_score INTEGER NOT NULL,
            away_score INTEGER NOT NULL,
            status TEXT DEFAULT 'Final',
            meta TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_game_stats_gamepk
        ON game_stats(game_pk)
    """)

    # Migration 2: Create reports_nhl table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports_nhl (
            id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration 3: Create reports_nhl_picks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports_nhl_picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT NOT NULL,
            label TEXT NOT NULL,
            market TEXT NOT NULL,
            odds REAL NOT NULL,
            fair_odds REAL NOT NULL,
            edge_pct REAL NOT NULL,
            confidence INTEGER NOT NULL,
            result TEXT DEFAULT 'pending',
            stake REAL NOT NULL,
            implied_prob REAL NOT NULL,
            game_pk INTEGER,
            meta TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            settled_at TEXT,
            FOREIGN KEY (report_id) REFERENCES reports_nhl(id),
            FOREIGN KEY (game_pk) REFERENCES game_stats(game_pk)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_reports_nhl_picks_report
        ON reports_nhl_picks(report_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_reports_nhl_picks_gamepk
        ON reports_nhl_picks(game_pk)
    """)

    # Migration 4: Create model_predictions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT NOT NULL,
            scope TEXT NOT NULL,
            lambda_home REAL NOT NULL,
            lambda_away REAL NOT NULL,
            meta TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_model_predictions_scope
        ON model_predictions(scope)
    """)

    # Migration 5: Create bankroll_state table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bankroll_state (
            date TEXT PRIMARY KEY,
            bankroll_start REAL NOT NULL,
            bankroll_end REAL NOT NULL,
            pnl REAL NOT NULL,
            roi REAL NOT NULL
        )
    """)

    # Migration 6: Create view for daily ROI
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS vw_roi_daily AS
        SELECT
            date,
            bankroll_start,
            bankroll_end,
            pnl,
            roi,
            (bankroll_end - bankroll_start) as daily_change
        FROM bankroll_state
        ORDER BY date DESC
    """)

    conn.commit()
    conn.close()
    print(f"✅ Database migrations completed: {db_path}")


if __name__ == "__main__":
    run_migrations()
