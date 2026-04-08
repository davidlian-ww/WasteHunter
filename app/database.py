"""Database setup and models for TIMWOOD Waste Dashboard with FMA Analysis"""
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

# Severity to RPN multiplier
SEVERITY_MULTIPLIER = {
    "Low": 1,
    "Medium": 5,
    "High": 7,
    "Critical": 10
}

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
    """Initialize database tables with FMA extensions"""
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
        
        # Process Steps table
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
        
        # Failure Mode Analysis (FMA) extensions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failure_modes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                observation_id INTEGER NOT NULL UNIQUE,
                occurrence_score INTEGER DEFAULT 3,
                detection_score INTEGER DEFAULT 3,
                root_cause TEXT,
                rpn_score INTEGER,
                impact_hours REAL DEFAULT 0,
                impact_cost REAL DEFAULT 0,
                mitigation_action TEXT,
                mitigation_owner TEXT,
                mitigation_due_date TEXT,
                mitigation_status TEXT DEFAULT 'Not Started',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (observation_id) REFERENCES waste_observations(id) ON DELETE CASCADE,
                CHECK (occurrence_score BETWEEN 1 AND 10),
                CHECK (detection_score BETWEEN 1 AND 10),
                CHECK (mitigation_status IN ('Not Started', 'In Progress', 'Completed', 'On Hold'))
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_paths_site ON process_paths(site_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_steps_path ON process_steps(path_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_step ON waste_observations(step_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_category ON waste_observations(waste_category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_observation ON comments(observation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_failure_modes_obs ON failure_modes(observation_id)")


# ── SITES ────────────────────────────────────────────────────────
def get_all_sites() -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT * FROM sites ORDER BY name").fetchall()
        return [dict(row) for row in rows]


def create_site(name: str, code: str, location: str = "", site_type: str = "FC") -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sites (name, code, location, type) VALUES (?, ?, ?, ?)",
            (name, code, location, site_type)
        )
        return cursor.lastrowid


# ── PROCESS PATHS ────────────────────────────────────────────────
def get_process_paths(site_id: Optional[int] = None) -> List[Dict[str, Any]]:
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
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO process_paths (site_id, name, description, created_by) VALUES (?, ?, ?, ?)",
            (site_id, name, description, created_by)
        )
        return cursor.lastrowid


# ── PROCESS STEPS ────────────────────────────────────────────────
def get_process_steps(path_id: int) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT * FROM process_steps WHERE path_id = ? ORDER BY step_order",
            (path_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def add_process_step(path_id: int, name: str, description: str = "") -> int:
    with get_db() as conn:
        cursor = conn.cursor()
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


# ── WASTE OBSERVATIONS ───────────────────────────────────────────
def get_waste_observations(step_id: Optional[int] = None, path_id: Optional[int] = None) -> List[Dict[str, Any]]:
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
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO waste_observations 
               (step_id, waste_category, title, description, severity, observed_by) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (step_id, waste_category, title, description, severity, observed_by)
        )
        return cursor.lastrowid


# ── COMMENTS ─────────────────────────────────────────────────────
def get_comments(observation_id: int) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT * FROM comments WHERE observation_id = ? ORDER BY created_at ASC",
            (observation_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def add_comment(observation_id: int, author: str, comment: str) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO comments (observation_id, author, comment) VALUES (?, ?, ?)",
            (observation_id, author, comment)
        )
        return cursor.lastrowid


# ── FAILURE MODE ANALYSIS ────────────────────────────────────────
def create_failure_mode(
    observation_id: int,
    occurrence_score: int = 3,
    detection_score: int = 3,
    root_cause: str = "",
    impact_hours: float = 0,
    impact_cost: float = 0
) -> int:
    """Create FMA record for observation"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO failure_modes 
               (observation_id, occurrence_score, detection_score, root_cause, impact_hours, impact_cost) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (observation_id, occurrence_score, detection_score, root_cause, impact_hours, impact_cost)
        )
        return cursor.lastrowid


def get_failure_mode(observation_id: int) -> Optional[Dict[str, Any]]:
    """Get FMA for observation"""
    with get_db() as conn:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM failure_modes WHERE observation_id = ?",
            (observation_id,)
        ).fetchone()
        return dict(row) if row else None


def update_failure_mode(
    observation_id: int,
    occurrence_score: Optional[int] = None,
    detection_score: Optional[int] = None,
    root_cause: Optional[str] = None,
    rpn_score: Optional[int] = None,
    impact_hours: Optional[float] = None,
    impact_cost: Optional[float] = None,
    mitigation_action: Optional[str] = None,
    mitigation_owner: Optional[str] = None,
    mitigation_due_date: Optional[str] = None,
    mitigation_status: Optional[str] = None
):
    """Update FMA record"""
    with get_db() as conn:
        cursor = conn.cursor()
        updates = []
        values = []
        
        if occurrence_score is not None:
            updates.append("occurrence_score = ?")
            values.append(occurrence_score)
        if detection_score is not None:
            updates.append("detection_score = ?")
            values.append(detection_score)
        if root_cause is not None:
            updates.append("root_cause = ?")
            values.append(root_cause)
        if rpn_score is not None:
            updates.append("rpn_score = ?")
            values.append(rpn_score)
        if impact_hours is not None:
            updates.append("impact_hours = ?")
            values.append(impact_hours)
        if impact_cost is not None:
            updates.append("impact_cost = ?")
            values.append(impact_cost)
        if mitigation_action is not None:
            updates.append("mitigation_action = ?")
            values.append(mitigation_action)
        if mitigation_owner is not None:
            updates.append("mitigation_owner = ?")
            values.append(mitigation_owner)
        if mitigation_due_date is not None:
            updates.append("mitigation_due_date = ?")
            values.append(mitigation_due_date)
        if mitigation_status is not None:
            updates.append("mitigation_status = ?")
            values.append(mitigation_status)
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(observation_id)
            query = f"UPDATE failure_modes SET {', '.join(updates)} WHERE observation_id = ?"
            cursor.execute(query, values)


def calculate_rpn(severity: str, occurrence: int, detection: int) -> int:
    """Calculate RPN: Severity × Occurrence × Detection"""
    severity_val = SEVERITY_MULTIPLIER.get(severity, 5)
    return severity_val * occurrence * detection


def get_fma_analytics() -> Dict[str, Any]:
    """Get comprehensive FMA analytics"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Top failure modes by RPN
        top_by_rpn = cursor.execute("""
            SELECT wo.id, wo.title, wo.waste_category, wo.severity,
                   fm.rpn_score, fm.occurrence_score, fm.detection_score,
                   fm.root_cause, fm.impact_cost, fm.impact_hours
            FROM waste_observations wo
            LEFT JOIN failure_modes fm ON wo.id = fm.observation_id
            WHERE fm.rpn_score IS NOT NULL
            ORDER BY fm.rpn_score DESC
            LIMIT 10
        """).fetchall()
        
        # Failure modes by waste category
        by_category = cursor.execute("""
            SELECT wo.waste_category, COUNT(*) as count,
                   AVG(fm.rpn_score) as avg_rpn
            FROM waste_observations wo
            LEFT JOIN failure_modes fm ON wo.id = fm.observation_id
            GROUP BY wo.waste_category
            ORDER BY count DESC
        """).fetchall()
        
        # Severity distribution
        severity_dist = cursor.execute("""
            SELECT wo.severity, COUNT(*) as count
            FROM waste_observations wo
            GROUP BY wo.severity
        """).fetchall()
        
        # Mitigation status
        mitigation_status = cursor.execute("""
            SELECT fm.mitigation_status, COUNT(*) as count
            FROM failure_modes fm
            GROUP BY fm.mitigation_status
        """).fetchall()
        
        # Total impact
        total_impact = cursor.execute("""
            SELECT 
                SUM(fm.impact_cost) as total_cost,
                SUM(fm.impact_hours) as total_hours,
                COUNT(*) as total_failures
            FROM failure_modes fm
        """).fetchone()
        
        return {
            "top_by_rpn": [dict(row) for row in top_by_rpn],
            "by_category": [dict(row) for row in by_category],
            "severity_dist": [dict(row) for row in severity_dist],
            "mitigation_status": [dict(row) for row in mitigation_status],
            "total_impact": dict(total_impact) if total_impact else {}
        }


# ── DASHBOARD STATS ──────────────────────────────────────────────
def get_dashboard_stats() -> Dict[str, Any]:
    """Get statistics for dashboard"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        total_sites = cursor.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
        total_paths = cursor.execute("SELECT COUNT(*) FROM process_paths").fetchone()[0]
        total_observations = cursor.execute("SELECT COUNT(*) FROM waste_observations").fetchone()[0]
        open_observations = cursor.execute(
            "SELECT COUNT(*) FROM waste_observations WHERE status = 'Open'"
        ).fetchone()[0]
        
        waste_by_category = cursor.execute("""
            SELECT waste_category, COUNT(*) as count
            FROM waste_observations
            GROUP BY waste_category
            ORDER BY count DESC
        """).fetchall()
        
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
        
        for step in path['steps']:
            step['observations'] = get_waste_observations(step_id=step['id'])
            for obs in step['observations']:
                comment_count = cursor.execute(
                    "SELECT COUNT(*) FROM comments WHERE observation_id = ?",
                    (obs['id'],)
                ).fetchone()[0]
                obs['comment_count'] = comment_count
                # Add FMA data
                fm = get_failure_mode(obs['id'])
                if fm:
                    obs['failure_mode'] = fm
        
        return path
