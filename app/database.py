"""Database setup and models for TIMWOOD Waste Dashboard"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, List, Any

DB_PATH = "timwood.db"

# TIMWOOD waste categories
WASTE_CATEGORIES = [
    "Transportation",
    "Inventory",
    "Motion",
    "Waiting",
    "Overproduction",
    "Over-processing",
    "Defects"
]

@contextmanager
def get_db():
    """Context manager for database connections"""
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


def init_db():
    """Initialize database tables"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # FCs/Sites table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                code TEXT NOT NULL UNIQUE,
                location TEXT,
                type TEXT DEFAULT 'FC',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Process Paths table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS process_paths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                created_by TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
            )
        """)
        
        # Process Steps table (ordered steps in a path)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS process_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path_id INTEGER NOT NULL,
                step_order INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (path_id) REFERENCES process_paths(id) ON DELETE CASCADE
            )
        """)
        
        # Waste Observations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS waste_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                step_id INTEGER NOT NULL,
                waste_category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                severity TEXT DEFAULT 'Medium',
                status TEXT DEFAULT 'Open',
                observed_by TEXT,
                observed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (step_id) REFERENCES process_steps(id) ON DELETE CASCADE,
                CHECK (waste_category IN ('Transportation', 'Inventory', 'Motion', 
                                          'Waiting', 'Overproduction', 'Over-processing', 'Defects')),
                CHECK (severity IN ('Low', 'Medium', 'High', 'Critical')),
                CHECK (status IN ('Open', 'In Progress', 'Resolved', 'Closed'))
            )
        """)
        
        # Comments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                observation_id INTEGER NOT NULL,
                author TEXT NOT NULL,
                comment TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (observation_id) REFERENCES waste_observations(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_paths_site ON process_paths(site_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_steps_path ON process_steps(path_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_step ON waste_observations(step_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_category ON waste_observations(waste_category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_observation ON comments(observation_id)")


# Helper functions for data access
def get_all_sites() -> List[Dict[str, Any]]:
    """Get all sites"""
    with get_db() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT * FROM sites ORDER BY name").fetchall()
        return [dict(row) for row in rows]


def create_site(name: str, code: str, location: str = "", site_type: str = "FC") -> int:
    """Create a new site"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sites (name, code, location, type) VALUES (?, ?, ?, ?)",
            (name, code, location, site_type)
        )
        return cursor.lastrowid


def get_process_paths(site_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get process paths, optionally filtered by site"""
    with get_db() as conn:
        cursor = conn.cursor()
        if site_id:
            query = """
                SELECT pp.*, s.name as site_name, s.code as site_code
                FROM process_paths pp
                JOIN sites s ON pp.site_id = s.id
                WHERE pp.site_id = ?
                ORDER BY pp.created_at DESC
            """
            rows = cursor.execute(query, (site_id,)).fetchall()
        else:
            query = """
                SELECT pp.*, s.name as site_name, s.code as site_code
                FROM process_paths pp
                JOIN sites s ON pp.site_id = s.id
                ORDER BY pp.created_at DESC
            """
            rows = cursor.execute(query).fetchall()
        return [dict(row) for row in rows]


def create_process_path(site_id: int, name: str, description: str = "", created_by: str = "User") -> int:
    """Create a new process path"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO process_paths (site_id, name, description, created_by) VALUES (?, ?, ?, ?)",
            (site_id, name, description, created_by)
        )
        return cursor.lastrowid


def get_process_steps(path_id: int) -> List[Dict[str, Any]]:
    """Get all steps for a process path"""
    with get_db() as conn:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT * FROM process_steps WHERE path_id = ? ORDER BY step_order",
            (path_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def add_process_step(path_id: int, name: str, description: str = "") -> int:
    """Add a step to a process path"""
    with get_db() as conn:
        cursor = conn.cursor()
        # Get next order number
        max_order = cursor.execute(
            "SELECT MAX(step_order) FROM process_steps WHERE path_id = ?",
            (path_id,)
        ).fetchone()[0]
        next_order = (max_order or 0) + 1
        
        cursor.execute(
            "INSERT INTO process_steps (path_id, step_order, name, description) VALUES (?, ?, ?, ?)",
            (path_id, next_order, name, description)
        )
        return cursor.lastrowid


def get_waste_observations(step_id: Optional[int] = None, path_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get waste observations, optionally filtered by step or path"""
    with get_db() as conn:
        cursor = conn.cursor()
        if step_id:
            query = """
                SELECT wo.*, ps.name as step_name, pp.name as path_name, s.name as site_name
                FROM waste_observations wo
                JOIN process_steps ps ON wo.step_id = ps.id
                JOIN process_paths pp ON ps.path_id = pp.id
                JOIN sites s ON pp.site_id = s.id
                WHERE wo.step_id = ?
                ORDER BY wo.observed_at DESC
            """
            rows = cursor.execute(query, (step_id,)).fetchall()
        elif path_id:
            query = """
                SELECT wo.*, ps.name as step_name, pp.name as path_name, s.name as site_name
                FROM waste_observations wo
                JOIN process_steps ps ON wo.step_id = ps.id
                JOIN process_paths pp ON ps.path_id = pp.id
                JOIN sites s ON pp.site_id = s.id
                WHERE ps.path_id = ?
                ORDER BY wo.observed_at DESC
            """
            rows = cursor.execute(query, (path_id,)).fetchall()
        else:
            query = """
                SELECT wo.*, ps.name as step_name, pp.name as path_name, s.name as site_name
                FROM waste_observations wo
                JOIN process_steps ps ON wo.step_id = ps.id
                JOIN process_paths pp ON ps.path_id = pp.id
                JOIN sites s ON pp.site_id = s.id
                ORDER BY wo.observed_at DESC
            """
            rows = cursor.execute(query).fetchall()
        return [dict(row) for row in rows]


def create_waste_observation(
    step_id: int,
    waste_category: str,
    title: str,
    description: str = "",
    severity: str = "Medium",
    observed_by: str = "User"
) -> int:
    """Create a new waste observation"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO waste_observations 
               (step_id, waste_category, title, description, severity, observed_by) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (step_id, waste_category, title, description, severity, observed_by)
        )
        return cursor.lastrowid


def get_comments(observation_id: int) -> List[Dict[str, Any]]:
    """Get all comments for an observation"""
    with get_db() as conn:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT * FROM comments WHERE observation_id = ? ORDER BY created_at ASC",
            (observation_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def add_comment(observation_id: int, author: str, comment: str) -> int:
    """Add a comment to an observation"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO comments (observation_id, author, comment) VALUES (?, ?, ?)",
            (observation_id, author, comment)
        )
        return cursor.lastrowid


def get_dashboard_stats() -> Dict[str, Any]:
    """Get statistics for dashboard"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Total counts
        total_sites = cursor.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
        total_paths = cursor.execute("SELECT COUNT(*) FROM process_paths").fetchone()[0]
        total_observations = cursor.execute("SELECT COUNT(*) FROM waste_observations").fetchone()[0]
        open_observations = cursor.execute(
            "SELECT COUNT(*) FROM waste_observations WHERE status = 'Open'"
        ).fetchone()[0]
        
        # Waste by category
        waste_by_category = cursor.execute("""
            SELECT waste_category, COUNT(*) as count
            FROM waste_observations
            GROUP BY waste_category
            ORDER BY count DESC
        """).fetchall()
        
        # Severity breakdown
        severity_breakdown = cursor.execute("""
            SELECT severity, COUNT(*) as count
            FROM waste_observations
            GROUP BY severity
        """).fetchall()
        
        return {
            "total_sites": total_sites,
            "total_paths": total_paths,
            "total_observations": total_observations,
            "open_observations": open_observations,
            "waste_by_category": [dict(row) for row in waste_by_category],
            "severity_breakdown": [dict(row) for row in severity_breakdown]
        }


def update_observation_status(observation_id: int, status: str) -> None:
    """Update observation status"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE waste_observations SET status = ? WHERE id = ?",
            (status, observation_id)
        )


def get_path_details(path_id: int) -> Optional[Dict[str, Any]]:
    """Get full details of a process path with steps and observations"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get path info
        path_row = cursor.execute("""
            SELECT pp.*, s.name as site_name, s.code as site_code
            FROM process_paths pp
            JOIN sites s ON pp.site_id = s.id
            WHERE pp.id = ?
        """, (path_id,)).fetchone()
        
        if not path_row:
            return None
        
        path = dict(path_row)
        path['steps'] = get_process_steps(path_id)
        
        # Add observations to each step
        for step in path['steps']:
            step['observations'] = get_waste_observations(step_id=step['id'])
            # Add comment count to each observation
            for obs in step['observations']:
                comment_count = cursor.execute(
                    "SELECT COUNT(*) FROM comments WHERE observation_id = ?",
                    (obs['id'],)
                ).fetchone()[0]
                obs['comment_count'] = comment_count
        
        return path
