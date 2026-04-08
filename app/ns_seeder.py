"""Seed all NS (Non-Sort) FC sites and their official IB/OB process paths.

Data source: Confluence — Non-Sortable FCs (SUPPLYCH) + E2E Manual Endgame (SCTNGMS)
Run on startup; idempotent (skips existing records).
"""
import logging
from app.database import get_db

log = logging.getLogger(__name__)

# ── NS Sites ─────────────────────────────────────────────────────────────────
# Source: Confluence E2E Manual Endgame + NS Conversion Plan
NS_SITES: list[dict] = [
    {"code": "ATL2", "name": "ATL2 Carrollton",    "location": "Carrollton, GA"},
    {"code": "ATL3", "name": "ATL3 Pendergrass",   "location": "Pendergrass, GA"},
    {"code": "BNA1", "name": "BNA1 Lebanon",        "location": "Lebanon, TN"},
    {"code": "CVG1", "name": "CVG1 Monroe",         "location": "Monroe, OH"},
    {"code": "DFW2", "name": "DFW2 Fort Worth",     "location": "Fort Worth, TX"},
    {"code": "IND2", "name": "IND2 Plainfield",     "location": "Plainfield, IN"},
    {"code": "LAX2", "name": "LAX2 Chino",          "location": "Chino, CA"},
    {"code": "LAX9", "name": "LAX9 Shafter",        "location": "Shafter, CA"},
    {"code": "MCO2", "name": "MCO2 Davenport",      "location": "Davenport, FL"},
    {"code": "MCI1", "name": "MCI1 Topeka",         "location": "Topeka, KS"},
    {"code": "PHL2", "name": "PHL2 Bethlehem",      "location": "Bethlehem, PA"},
    {"code": "PHL4", "name": "PHL4 Shippensburg",   "location": "Shippensburg, PA"},
    {"code": "PHX1", "name": "PHX1 Litchfield Park","location": "Litchfield Park, AZ"},
    {"code": "SLC1", "name": "SLC1 Salt Lake City", "location": "Salt Lake City, UT"},
    {"code": "SMF1", "name": "SMF1 Sacramento",     "location": "Sacramento, CA"},
]

# ── Process Paths + Steps ─────────────────────────────────────────────────────
# Source: FCAM Activity Framework — Non-Sortable FCs (SUPPLYCH)
# Hierarchy: Path (department) → Steps (activities)
NS_PATHS: list[dict] = [
    {
        "name": "IB – Inbound",
        "description": "All inbound receiving operations (FCAM IB Activity Framework)",
        "steps": [
            ("Unloading",                       "Removing IB cases/pallets from trailer to building"),
            ("Receiving Management / GDM",      "Managing inbound deliveries and POs via GLS/GDM"),
            ("Slotting",                        "Determining prime location assignment for each SKU"),
            ("Hauling",                         "Transporting pallets from receiving dock to storage zone"),
            ("Stocking (Pick Module – Eaches)", "Putting decanted items away in pick module bin locations"),
            ("Putaway (Case / Pallet)",         "Placing an entire case or pallet in reserve/prime location"),
            ("Topoff",                          "Adding partial receipt onto existing prime pallet if space allows"),
            ("First Time SKU (FTS)",            "Capturing item attributes for new SKUs (dims, flags, velocity)"),
            ("Inbound Problem Solve (IPS)",     "Resolving overages, misships, damage, or missing POs"),
            ("ODV (Outbound Delivery Verify)",  "FC associates verify inbound receipt accuracy"),
            ("IB Exceptions / Rework",          "Rework for missing poly bag, UPC, or prep requirements"),
        ],
    },
    {
        "name": "OB – Outbound",
        "description": "All outbound fulfillment operations (FCAM OB Activity Framework)",
        "steps": [
            ("Replenishment",              "Moving items from reserve/storage to pickable prime location"),
            ("Wave Drop / Work Assignment","AM drops waves in WMS and assigns orderfilling work"),
            ("Orderfilling / Picking",     "Picking items for customer orders via RF scanner trip"),
            ("Packing (Non-Ship-As-Is)",   "Packing non-SAI items through Packsize or manual carton"),
            ("Ship As Is (SAI) Processing","Processing items that ship in vendor box without overbox"),
            ("Non-Conveyable Handling",    "Special handling for oversized or non-conveyable items"),
            ("Staging / Sort",             "Staging picked items at correct dock door by sort code"),
            ("Loading / Shipping",         "Loading pallets/floor-stacked freight onto OB trailer"),
            ("OB Exceptions",              "Handling short picks, misloads, or carrier issues"),
        ],
    },
    {
        "name": "Returns",
        "description": "Reverse logistics and returns processing",
        "steps": [
            ("Returns Receive (RTV / RTF)", "Receiving returned items from customers or stores"),
            ("Returns Assess / Grade",      "Grading returns as sellable, donate, or dispose"),
            ("Returns Stow",               "Putting graded returns into appropriate storage location"),
            ("Returns Dispose / Liquidate","Processing items for liquidation or disposal"),
        ],
    },
    {
        "name": "Inventory Control (IC)",
        "description": "Inventory accuracy and reconciliation activities",
        "steps": [
            ("Cycle Count",             "Scheduled count of locations to verify system inventory"),
            ("Research & Reconcile",    "Investigating and resolving inventory discrepancies"),
            ("Location Audit",          "Physical audit of pick/reserve locations for accuracy"),
            ("Lost & Found",            "Locating items with no home location or wrong placement"),
        ],
    },
    {
        "name": "Quality & Safety",
        "description": "Quality assurance and safety observation activities",
        "steps": [
            ("Inbound Quality Check",  "Verifying inbound product quality and condition"),
            ("Outbound Quality Check", "Verifying outbound order accuracy before shipping"),
            ("Defect Investigation",   "Root cause analysis for defective or damaged items"),
            ("SOP Compliance Audit",   "Checking associate adherence to standard work procedures"),
            ("Safety Observation",     "Identifying and logging unsafe acts or conditions"),
        ],
    },
    {
        "name": "Support / Enabling",
        "description": "Support functions enabling FC operations",
        "steps": [
            ("Maintenance / Engineering", "Equipment maintenance and engineering support"),
            ("Facilities / Housekeeping", "Building cleanliness and facility management"),
            ("IT / Systems",             "Technology support and system issues"),
            ("Loss Prevention (LP)",     "Asset protection and loss prevention activities"),
            ("HR / People / Training",   "Human resources and associate development"),
            ("Leadership / Admin",       "Management oversight and administrative tasks"),
        ],
    },
]


# ── Seed Functions ────────────────────────────────────────────────────────────

def _get_or_create_site(cursor, site: dict) -> int:
    row = cursor.execute(
        "SELECT id FROM sites WHERE code = ?", (site["code"],)
    ).fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO sites (name, code, location, type) VALUES (?, ?, ?, 'FC')",
        (site["name"], site["code"], site["location"]),
    )
    return cursor.lastrowid


def _get_or_create_path(cursor, site_id: int, path: dict) -> int:
    row = cursor.execute(
        "SELECT id FROM process_paths WHERE site_id = ? AND name = ?",
        (site_id, path["name"]),
    ).fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO process_paths (site_id, name, description, created_by) VALUES (?, ?, ?, 'NS Seeder')",
        (site_id, path["name"], path["description"]),
    )
    return cursor.lastrowid


def _seed_steps(cursor, path_id: int, steps: list[tuple]) -> None:
    existing = {
        r[0] for r in cursor.execute(
            "SELECT name FROM process_steps WHERE path_id = ?", (path_id,)
        ).fetchall()
    }
    for order, (name, desc) in enumerate(steps, start=1):
        if name not in existing:
            cursor.execute(
                "INSERT INTO process_steps (path_id, step_order, name, description) VALUES (?, ?, ?, ?)",
                (path_id, order, name, desc),
            )


def seed_ns_sites() -> None:
    """Idempotent: create all NS FC sites and their IB/OB process paths + steps."""
    with get_db() as conn:
        cursor = conn.cursor()
        sites_added = paths_added = steps_added = 0

        for site_def in NS_SITES:
            prev_site_count = cursor.execute("SELECT COUNT(*) FROM sites WHERE code=?", (site_def["code"],)).fetchone()[0]
            site_id = _get_or_create_site(cursor, site_def)
            if prev_site_count == 0:
                sites_added += 1

            for path_def in NS_PATHS:
                prev_path_count = cursor.execute(
                    "SELECT COUNT(*) FROM process_paths WHERE site_id=? AND name=?",
                    (site_id, path_def["name"]),
                ).fetchone()[0]
                path_id = _get_or_create_path(cursor, site_id, path_def)
                if prev_path_count == 0:
                    paths_added += 1

                prev_step_count = cursor.execute(
                    "SELECT COUNT(*) FROM process_steps WHERE path_id=?", (path_id,)
                ).fetchone()[0]
                _seed_steps(cursor, path_id, path_def["steps"])
                steps_added += cursor.execute(
                    "SELECT COUNT(*) FROM process_steps WHERE path_id=?", (path_id,)
                ).fetchone()[0] - prev_step_count

        log.info(
            "NS seeder: %d sites, %d paths, %d steps added.",
            sites_added, paths_added, steps_added,
        )
