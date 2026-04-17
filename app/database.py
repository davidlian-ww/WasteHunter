"""Database setup and models for TIMWOOD Waste Dashboard with FMA Analysis"""
import csv
import io
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple

DB_PATH = "timwood.db"

# TIMWOOD waste categories
WASTE_CATEGORIES = [
    "Transportation",
    "Inventory",
    "Motion",
    "Waiting",
    "Overproduction",
    "Over-processing",
    "Defects",
    "Safety",
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
    """Context manager for database connections.
    WAL mode = concurrent readers + one writer, safe for multi-user.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=8000")
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
                                          'Waiting', 'Overproduction', 'Over-processing',
                                          'Defects', 'Safety')),
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
        
        # ── Migration: add observation_duration_seconds if the column is missing ──
        try:
            cursor.execute(
                "ALTER TABLE waste_observations ADD COLUMN observation_duration_seconds INTEGER DEFAULT NULL"
            )
        except Exception:
            pass  # Column already exists — sqlite3 raises OperationalError, not a problem

        # ── PWA observations (raw sync from atlas-fmo PWA) ──────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pwa_observations (
                id            INTEGER PRIMARY KEY,
                observer      TEXT,
                site          TEXT,
                shift         TEXT,
                process_path  TEXT,
                observer_area TEXT,
                waste_category TEXT,
                title         TEXT NOT NULL,
                description   TEXT,
                severity      TEXT,
                timestamp     TEXT,
                observation_duration_seconds INTEGER,
                received_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_paths_site ON process_paths(site_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_steps_path ON process_steps(path_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_step ON waste_observations(step_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_category ON waste_observations(waste_category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_observation ON comments(observation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_failure_modes_obs ON failure_modes(observation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pwa_site ON pwa_observations(site)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pwa_ts   ON pwa_observations(timestamp)")

    # Run after the main with-block so it gets its own connection
    _migrate_waste_category_safety()


def _migrate_waste_category_safety():
    """Recreate waste_observations with Safety in the CHECK constraint if needed.
    SQLite doesn't support ALTER TABLE … MODIFY CONSTRAINT, so we use the
    standard rename-copy-drop-rename pattern.  Idempotent.
    """
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='waste_observations'"
        ).fetchone()
        if row and "'Safety'" in row[0]:
            return  # already migrated
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS waste_observations_v2 (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                step_id     INTEGER NOT NULL,
                waste_category TEXT NOT NULL,
                title       TEXT NOT NULL,
                description TEXT,
                severity    TEXT DEFAULT 'Medium',
                status      TEXT DEFAULT 'Open',
                observed_by TEXT,
                observed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                observation_duration_seconds INTEGER DEFAULT NULL,
                FOREIGN KEY (step_id) REFERENCES process_steps(id) ON DELETE CASCADE,
                CHECK (waste_category IN ('Transportation','Inventory','Motion',
                                         'Waiting','Overproduction','Over-processing',
                                         'Defects','Safety')),
                CHECK (severity IN ('Low','Medium','High','Critical')),
                CHECK (status IN ('Open','In Progress','Resolved','Closed'))
            );
            INSERT INTO waste_observations_v2
                SELECT id, step_id, waste_category, title, description,
                       severity, status, observed_by, observed_at,
                       observation_duration_seconds
                FROM   waste_observations;
            DROP TABLE waste_observations;
            ALTER TABLE waste_observations_v2 RENAME TO waste_observations;
            CREATE INDEX IF NOT EXISTS idx_observations_step
                ON waste_observations(step_id);
            CREATE INDEX IF NOT EXISTS idx_observations_category
                ON waste_observations(waste_category);
        """)
        conn.execute("PRAGMA foreign_keys=ON")


# ── SITES ──────────────────────────────────────────────────────────────
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


# ── QUICK LOG (user-facing entry point) ─────────────────────────
_DEFAULT_SITE_NAME = "FMO Tracker"
_DEFAULT_SITE_CODE = "FMO"


def _ensure_default_site() -> int:
    """Get or create the hidden default site."""
    with get_db() as conn:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT id FROM sites WHERE code = ?", (_DEFAULT_SITE_CODE,)
        ).fetchone()
        if row:
            return row[0]
        cursor.execute(
            "INSERT INTO sites (name, code, type) VALUES (?, ?, 'FC')",
            (_DEFAULT_SITE_NAME, _DEFAULT_SITE_CODE),
        )
        return cursor.lastrowid


def get_or_create_process_path(path_name: str) -> int:
    """Return the step_id for a path's 'General' step, creating as needed."""
    site_id = _ensure_default_site()
    path_name = path_name.strip()
    with get_db() as conn:
        cursor = conn.cursor()
        # Find existing path
        row = cursor.execute(
            "SELECT id FROM process_paths WHERE site_id = ? AND name = ?",
            (site_id, path_name),
        ).fetchone()
        if row:
            path_id = row[0]
        else:
            cursor.execute(
                "INSERT INTO process_paths (site_id, name, created_by) VALUES (?, ?, 'Quick Log')",
                (site_id, path_name),
            )
            path_id = cursor.lastrowid

        # Find or create General step
        step_row = cursor.execute(
            "SELECT id FROM process_steps WHERE path_id = ? AND name = 'General'",
            (path_id,),
        ).fetchone()
        if step_row:
            return step_row[0]
        cursor.execute(
            "INSERT INTO process_steps (path_id, step_order, name) VALUES (?, 1, 'General')",
            (path_id,),
        )
        return cursor.lastrowid


def quick_log_observation(
    process_path: str,
    waste_category: str,
    title: str,
    description: str = "",
    severity: str = "Medium",
    observed_by: str = "Anonymous",
    initial_comment: str = "",
    observation_duration_seconds: Optional[int] = None,
) -> int:
    """One-shot: create observation (+ FMA + optional comment) from a path name."""
    step_id = get_or_create_process_path(process_path)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO waste_observations
               (step_id, waste_category, title, description, severity, observed_by,
                observation_duration_seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (step_id, waste_category, title, description, severity, observed_by,
             observation_duration_seconds),
        )
        obs_id = cursor.lastrowid
        # Auto FMA record
        cursor.execute(
            """INSERT INTO failure_modes
               (observation_id, occurrence_score, detection_score)
               VALUES (?, 3, 3)""",
            (obs_id,),
        )
        # Optional initial comment
        if initial_comment.strip():
            cursor.execute(
                "INSERT INTO comments (observation_id, author, comment) VALUES (?, ?, ?)",
                (obs_id, observed_by, initial_comment.strip()),
            )
    return obs_id


def get_all_process_path_names() -> List[str]:
    """Distinct path names for the datalist autocomplete."""
    with get_db() as conn:
        rows = conn.cursor().execute(
            "SELECT DISTINCT name FROM process_paths ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]


def get_recent_observations(limit: int = 50) -> List[Dict[str, Any]]:
    """Recent observations enriched with path name and comment list."""
    with get_db() as conn:
        cursor = conn.cursor()
        rows = cursor.execute(
            """
            SELECT wo.id, wo.title, wo.description, wo.waste_category,
                   wo.severity, wo.status, wo.observed_by, wo.observed_at,
                   wo.observation_duration_seconds,
                   pp.name AS path_name
            FROM waste_observations wo
            JOIN process_steps ps ON wo.step_id = ps.id
            JOIN process_paths pp ON ps.path_id = pp.id
            ORDER BY wo.observed_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        observations = [dict(r) for r in rows]
        for obs in observations:
            obs["comments"] = get_comments(obs["id"])
        return observations


# ── MICROSOFT FORMS CSV IMPORT ─────────────────────────────────────
# Column aliases: keys are what we look for (lowercase), value is our field.
_COL_MAP = {
    "process path":      "process_path",
    "waste category":    "waste_category",
    "observation title": "title",
    "details":           "description",
    "severity":          "severity",
    "your name":         "observed_by",
    "initial comment / notes": "initial_comment",
    "initial comment":   "initial_comment",
    "notes":             "initial_comment",
    "comment":           "initial_comment",
}

_VALID_CATEGORIES = {
    "transportation", "inventory", "motion", "waiting",
    "overproduction", "over-processing", "defects", "safety",
}
_VALID_SEVERITIES = {"low", "medium", "high", "critical"}


def import_from_forms_csv(csv_bytes: bytes) -> Tuple[int, int, List[str]]:
    """Parse a Microsoft Forms CSV export and import each row as an FMO.

    Returns: (imported_count, skipped_count, list_of_error_messages)
    """
    text = csv_bytes.decode("utf-8-sig")  # strip BOM that Excel adds
    reader = csv.DictReader(io.StringIO(text))

    imported, skipped = 0, 0
    errors: List[str] = []

    for row_num, raw_row in enumerate(reader, start=2):  # row 1 = header
        # Build a lowercase-key dict for fuzzy column matching
        row = {k.strip().lower(): v.strip() for k, v in raw_row.items() if k}

        # Map columns
        mapped: Dict[str, str] = {}
        for col_key, field in _COL_MAP.items():
            for raw_key, val in row.items():
                if col_key in raw_key:
                    mapped.setdefault(field, val)

        # Required fields check
        missing = [f for f in ("process_path", "waste_category", "title") if not mapped.get(f)]
        if missing:
            skipped += 1
            errors.append(f"Row {row_num}: missing {', '.join(missing)} — skipped.")
            continue

        # Validate category
        cat = mapped["waste_category"]
        if cat.lower() not in _VALID_CATEGORIES:
            # Try to fuzzy-match first letter
            letter = cat[0].upper() if cat else ""
            letter_map = {"T": "Transportation", "I": "Inventory", "M": "Motion",
                          "W": "Waiting", "O": "Overproduction", "D": "Defects",
                          "S": "Safety"}
            cat = letter_map.get(letter, "Waiting")
        else:
            # Normalize capitalisation
            cat = next(c for c in WASTE_CATEGORIES if c.lower() == cat.lower())

        # Validate severity
        sev = mapped.get("severity", "Medium")
        if sev.lower() not in _VALID_SEVERITIES:
            sev = "Medium"
        else:
            sev = sev.capitalize()

        try:
            quick_log_observation(
                process_path=mapped["process_path"],
                waste_category=cat,
                title=mapped["title"],
                description=mapped.get("description", ""),
                severity=sev,
                observed_by=mapped.get("observed_by", "Forms Import") or "Forms Import",
                initial_comment=mapped.get("initial_comment", ""),
            )
            imported += 1
        except Exception as exc:
            skipped += 1
            errors.append(f"Row {row_num}: import failed — {exc}")

    return imported, skipped, errors


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


# ── PWA OBSERVATIONS (atlas-fmo sync) ────────────────────────────────

def upsert_pwa_observation(entry: Dict[str, Any]) -> bool:
    """Insert or replace a PWA observation. Returns True if it was new."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM pwa_observations WHERE id=?", (entry["id"],)
        ).fetchone()
        conn.execute("""
            INSERT OR REPLACE INTO pwa_observations
                (id, observer, site, shift, process_path, observer_area,
                 waste_category, title, description, severity, timestamp,
                 observation_duration_seconds)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            entry.get("id"),
            entry.get("observer", "Anonymous"),
            entry.get("site", ""),
            entry.get("shift", ""),
            entry.get("process_path", ""),
            entry.get("observer_area", ""),
            entry.get("waste_category", ""),
            entry.get("title", ""),
            entry.get("description", ""),
            entry.get("severity", "Medium"),
            entry.get("timestamp"),
            entry.get("observation_duration_seconds"),
        ))
        return existing is None


def get_pwa_observations(site: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
    """Fetch PWA observations, newest first."""
    with get_db() as conn:
        if site:
            rows = conn.execute(
                "SELECT * FROM pwa_observations WHERE site=? ORDER BY timestamp DESC LIMIT ?",
                (site, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM pwa_observations ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
