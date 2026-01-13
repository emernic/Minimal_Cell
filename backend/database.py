"""
Database module for storing simulation state and results.
Uses SQLite for simplicity - single file, no external services.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

# Database file location - use environment variable or default
DB_PATH = os.environ.get("SIMULATION_DB_PATH", "/data/simulations.db")


def get_db_path() -> str:
    """Get database path, creating directory if needed."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    return DB_PATH


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(get_db_path(), timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database schema."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Simulations table - tracks simulation runs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulations (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                config TEXT,
                total_time_seconds INTEGER DEFAULT 3600,
                current_time_seconds INTEGER DEFAULT 0
            )
        """)

        # Results table - stores time-series data for each simulation
        # Each row is one timestep of simulation output
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id TEXT NOT NULL,
                time_seconds REAL NOT NULL,
                metabolites TEXT,
                fluxes TEXT,
                cell_metrics TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (simulation_id) REFERENCES simulations(id),
                UNIQUE(simulation_id, time_seconds)
            )
        """)

        # Index for efficient queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_sim_time
            ON results(simulation_id, time_seconds)
        """)


# ----- Simulation CRUD operations -----

def create_simulation(
    simulation_id: str,
    config: Optional[Dict] = None,
    total_time_seconds: int = 3600
) -> Dict:
    """Create a new simulation record."""
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        config_json = json.dumps(config) if config else None

        cursor.execute("""
            INSERT INTO simulations (id, status, created_at, config, total_time_seconds)
            VALUES (?, 'pending', ?, ?, ?)
        """, (simulation_id, now, config_json, total_time_seconds))

    # Get the created simulation (after commit)
    return get_simulation(simulation_id)


def get_simulation(simulation_id: str) -> Optional[Dict]:
    """Get simulation by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM simulations WHERE id = ?", (simulation_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def list_simulations(limit: int = 100, offset: int = 0) -> List[Dict]:
    """List all simulations, most recent first."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM simulations
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        return [dict(row) for row in cursor.fetchall()]


def update_simulation_status(
    simulation_id: str,
    status: str,
    error_message: Optional[str] = None,
    current_time_seconds: Optional[int] = None
):
    """Update simulation status."""
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        updates = ["status = ?"]
        params = [status]

        if status == "running":
            updates.append("started_at = ?")
            params.append(now)
        elif status in ("completed", "failed"):
            updates.append("completed_at = ?")
            params.append(now)

        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)

        if current_time_seconds is not None:
            updates.append("current_time_seconds = ?")
            params.append(current_time_seconds)

        params.append(simulation_id)

        cursor.execute(f"""
            UPDATE simulations
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)


def delete_simulation(simulation_id: str):
    """Delete a simulation and its results."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM results WHERE simulation_id = ?", (simulation_id,))
        cursor.execute("DELETE FROM simulations WHERE id = ?", (simulation_id,))


# ----- Results operations -----

def save_result(
    simulation_id: str,
    time_seconds: float,
    metabolites: Optional[Dict] = None,
    fluxes: Optional[Dict] = None,
    cell_metrics: Optional[Dict] = None
):
    """Save a single timestep result."""
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO results
            (simulation_id, time_seconds, metabolites, fluxes, cell_metrics, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            simulation_id,
            time_seconds,
            json.dumps(metabolites) if metabolites else None,
            json.dumps(fluxes) if fluxes else None,
            json.dumps(cell_metrics) if cell_metrics else None,
            now
        ))

        # Update simulation progress
        cursor.execute("""
            UPDATE simulations
            SET current_time_seconds = ?
            WHERE id = ?
        """, (int(time_seconds), simulation_id))


def get_results(
    simulation_id: str,
    after_time: Optional[float] = None,
    limit: int = 1000
) -> List[Dict]:
    """Get results for a simulation, optionally after a specific time."""
    with get_connection() as conn:
        cursor = conn.cursor()

        if after_time is not None:
            cursor.execute("""
                SELECT * FROM results
                WHERE simulation_id = ? AND time_seconds > ?
                ORDER BY time_seconds ASC
                LIMIT ?
            """, (simulation_id, after_time, limit))
        else:
            cursor.execute("""
                SELECT * FROM results
                WHERE simulation_id = ?
                ORDER BY time_seconds ASC
                LIMIT ?
            """, (simulation_id, limit))

        results = []
        for row in cursor.fetchall():
            result = dict(row)
            # Parse JSON fields
            if result.get('metabolites'):
                result['metabolites'] = json.loads(result['metabolites'])
            if result.get('fluxes'):
                result['fluxes'] = json.loads(result['fluxes'])
            if result.get('cell_metrics'):
                result['cell_metrics'] = json.loads(result['cell_metrics'])
            results.append(result)

        return results


def get_latest_result(simulation_id: str) -> Optional[Dict]:
    """Get the most recent result for a simulation."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM results
            WHERE simulation_id = ?
            ORDER BY time_seconds DESC
            LIMIT 1
        """, (simulation_id,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            if result.get('metabolites'):
                result['metabolites'] = json.loads(result['metabolites'])
            if result.get('fluxes'):
                result['fluxes'] = json.loads(result['fluxes'])
            if result.get('cell_metrics'):
                result['cell_metrics'] = json.loads(result['cell_metrics'])
            return result
        return None


def get_result_count(simulation_id: str) -> int:
    """Get the number of results for a simulation."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM results WHERE simulation_id = ?",
            (simulation_id,)
        )
        return cursor.fetchone()[0]
