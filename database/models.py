"""Database models for NHL Automation System."""
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from config.config import DATABASE_PATH


class Database:
    """SQLite database manager."""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Ensure database file exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        return cursor

    def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch one row."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def fetchall(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all rows."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


class GameStats:
    """Game statistics model."""

    def __init__(self, db: Database):
        self.db = db

    def create(
        self,
        game_pk: int,
        game_date: str,
        home_team: str,
        away_team: str,
        home_score: int,
        away_score: int,
        status: str = 'Final',
        meta: Optional[Dict[str, Any]] = None
    ) -> int:
        """Create a game stat record."""
        query = """
            INSERT INTO game_stats (
                game_pk, game_date, home_team, away_team,
                home_score, away_score, status, meta
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(game_pk) DO UPDATE SET
                home_score = excluded.home_score,
                away_score = excluded.away_score,
                status = excluded.status,
                meta = excluded.meta
        """
        cursor = self.db.execute(
            query,
            (game_pk, game_date, home_team, away_team, home_score, away_score, status, json.dumps(meta or {}))
        )
        return cursor.lastrowid

    def get_recent_games(self, days: int = 30) -> List[Dict]:
        """Get recent games for model training."""
        query = """
            SELECT * FROM game_stats
            WHERE game_date >= date('now', '-' || ? || ' days')
            AND status = 'Final'
            ORDER BY game_date DESC
        """
        return self.db.fetchall(query, (days,))

    def get_by_game_pk(self, game_pk: int) -> Optional[Dict]:
        """Get game by game_pk."""
        query = "SELECT * FROM game_stats WHERE game_pk = ?"
        return self.db.fetchone(query, (game_pk,))


class Report:
    """Report model."""

    def __init__(self, db: Database):
        self.db = db

    def create(self, report_type: str, content: str) -> str:
        """Create a report."""
        query = """
            INSERT INTO reports_nhl (type, content)
            VALUES (?, ?)
        """
        cursor = self.db.execute(query, (report_type, content))

        # Get the UUID that was generated
        result = self.db.fetchone(
            "SELECT id FROM reports_nhl WHERE rowid = ?",
            (cursor.lastrowid,)
        )
        return result['id'] if result else None

    def get_latest_by_type(self, report_type: str) -> Optional[Dict]:
        """Get latest report by type."""
        query = """
            SELECT * FROM reports_nhl
            WHERE type = ?
            ORDER BY created_at DESC
            LIMIT 1
        """
        return self.db.fetchone(query, (report_type,))


class Pick:
    """Pick model."""

    def __init__(self, db: Database):
        self.db = db

    def create(
        self,
        report_id: str,
        label: str,
        market: str,
        odds: float,
        fair_odds: float,
        edge_pct: float,
        confidence: int,
        stake: float,
        implied_prob: float,
        game_pk: Optional[int] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> int:
        """Create a pick."""
        query = """
            INSERT INTO reports_nhl_picks (
                report_id, label, market, odds, fair_odds, edge_pct,
                confidence, stake, implied_prob, game_pk, meta, result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """
        cursor = self.db.execute(
            query,
            (report_id, label, market, odds, fair_odds, edge_pct,
             confidence, stake, implied_prob, game_pk, json.dumps(meta or {}))
        )
        return cursor.lastrowid

    def get_pending_picks(self) -> List[Dict]:
        """Get all pending picks."""
        query = """
            SELECT * FROM reports_nhl_picks
            WHERE result = 'pending'
            ORDER BY created_at ASC
        """
        return self.db.fetchall(query)

    def settle_pick(self, pick_id: int, result: str):
        """Settle a pick (win/lose)."""
        query = """
            UPDATE reports_nhl_picks
            SET result = ?, settled_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        self.db.execute(query, (result, pick_id))

    def get_picks_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get picks within date range."""
        query = """
            SELECT * FROM reports_nhl_picks
            WHERE DATE(created_at) BETWEEN ? AND ?
            ORDER BY created_at DESC
        """
        return self.db.fetchall(query, (start_date, end_date))


class ModelPrediction:
    """Model prediction model."""

    def __init__(self, db: Database):
        self.db = db

    def create(
        self,
        model: str,
        scope: str,
        lambda_home: float,
        lambda_away: float,
        meta: Optional[Dict[str, Any]] = None
    ) -> int:
        """Create a model prediction record."""
        query = """
            INSERT INTO model_predictions (
                model, scope, lambda_home, lambda_away, meta
            ) VALUES (?, ?, ?, ?, ?)
        """
        cursor = self.db.execute(
            query,
            (model, scope, lambda_home, lambda_away, json.dumps(meta or {}))
        )
        return cursor.lastrowid

    def get_latest_by_scope(self, scope: str) -> Optional[Dict]:
        """Get latest model prediction by scope."""
        query = """
            SELECT * FROM model_predictions
            WHERE scope = ?
            ORDER BY created_at DESC
            LIMIT 1
        """
        return self.db.fetchone(query, (scope,))


class BankrollState:
    """Bankroll state model."""

    def __init__(self, db: Database):
        self.db = db

    def create(
        self,
        date: str,
        bankroll_start: float,
        bankroll_end: float,
        pnl: float,
        roi: float
    ):
        """Create or update bankroll state."""
        query = """
            INSERT INTO bankroll_state (date, bankroll_start, bankroll_end, pnl, roi)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                bankroll_end = excluded.bankroll_end,
                pnl = excluded.pnl,
                roi = excluded.roi
        """
        self.db.execute(query, (date, bankroll_start, bankroll_end, pnl, roi))

    def get_latest(self) -> Optional[Dict]:
        """Get latest bankroll state."""
        query = """
            SELECT * FROM bankroll_state
            ORDER BY date DESC
            LIMIT 1
        """
        return self.db.fetchone(query)

    def get_by_date(self, date: str) -> Optional[Dict]:
        """Get bankroll state by date."""
        query = "SELECT * FROM bankroll_state WHERE date = ?"
        return self.db.fetchone(query, (date,))
