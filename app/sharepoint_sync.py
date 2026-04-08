"""SharePoint → SQLite sync for FMO Observations list.

Auth: MSAL device-code flow (browser sign-in, token cached locally).
      First call opens a browser; subsequent calls use the refresh token.
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

try:
    import msal
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False

from app.database import get_db, quick_log_observation

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
# Microsoft Graph Explorer public client — broadly trusted, device-code capable
_CLIENT_ID   = "de8bc8b5-d9f9-48b1-a8ad-b748da725064"
_AUTHORITY   = "https://login.microsoftonline.com/organizations"
_SCOPES      = ["Sites.Read.All"]
_TOKEN_CACHE = Path("sp_token_cache.json")

# IND2 Leaders Team — confirmed owner access
_SITE_ID     = ("teams.wal-mart.com,165f2961-7d0e-4351-a03b-a49c2b592b07,"
                "ca4a8a12-fd6f-476d-ac67-87fd498e0cbe")
_LIST_NAME   = "FMO Observations"

# ── SharePoint form URL (floor leaders bookmark this) ────────────────────────
SHAREPOINT_FORM_URL = (
    "https://teams.wal-mart.com/sites/IND2LeadersTeam"
    "/Lists/FMO%20Observations/NewForm.aspx"
)

# ── Column name → DB field mapping ───────────────────────────────────────────
_FIELD_MAP = {
    "Title":        "title",
    "ObserverName": "observed_by",
    "ProcessPath":  "process_path",
    "WasteCategory":"waste_category",
    "Severity":     "severity",
    "Details":      "description",
    "Comments":     "initial_comment",
}


# ── Token management ─────────────────────────────────────────────────────────
def _load_cache() -> "msal.SerializableTokenCache":
    cache = msal.SerializableTokenCache()
    if _TOKEN_CACHE.exists():
        cache.deserialize(_TOKEN_CACHE.read_text())
    return cache


def _save_cache(cache: "msal.SerializableTokenCache") -> None:
    if cache.has_state_changed:
        _TOKEN_CACHE.write_text(cache.serialize())


def get_access_token() -> Optional[str]:
    """Return a valid access token, triggering device-code flow if needed."""
    if not MSAL_AVAILABLE:
        log.error("msal not installed — run: uv pip install msal")
        return None

    cache = _load_cache()
    app   = msal.PublicClientApplication(
        _CLIENT_ID, authority=_AUTHORITY, token_cache=cache
    )

    # Try silent first (uses cached refresh token)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(_SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _save_cache(cache)
            return result["access_token"]

    # Fall back to device-code flow
    flow = app.initiate_device_flow(_SCOPES)
    if "user_code" not in flow:
        log.error("Device flow failed: %s", flow.get("error_description"))
        return None

    # Return the flow so the caller can show the user what to do
    raise DeviceCodeRequired(flow["message"], flow)


class DeviceCodeRequired(Exception):
    """Raised when device-code auth is needed. message = user instructions."""
    def __init__(self, message: str, flow: dict):
        super().__init__(message)
        self.message = message
        self.flow    = flow

    def complete(self) -> Optional[str]:
        """Block until user completes sign-in, return token."""
        cache  = _load_cache()
        app    = msal.PublicClientApplication(
            _CLIENT_ID, authority=_AUTHORITY, token_cache=cache
        )
        result = app.acquire_token_by_device_flow(self.flow)
        _save_cache(cache)
        return result.get("access_token")


# ── Ensure tracking table exists ─────────────────────────────────────────────
def _ensure_sync_table() -> None:
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sp_sync (
                sp_item_id   TEXT PRIMARY KEY,
                obs_id       INTEGER NOT NULL,
                synced_at    TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def _already_synced(sp_item_id: str) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM sp_sync WHERE sp_item_id = ?", (sp_item_id,)
        ).fetchone()
        return row is not None


def _record_sync(sp_item_id: str, obs_id: int) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sp_sync (sp_item_id, obs_id) VALUES (?, ?)",
            (sp_item_id, obs_id),
        )


# ── Core sync logic ───────────────────────────────────────────────────────────
def fetch_sp_items(token: str) -> List[Dict[str, Any]]:
    """Pull all items from the FMO Observations SharePoint list."""
    url = (
        f"https://graph.microsoft.com/v1.0/sites/{_SITE_ID}"
        f"/lists/{_LIST_NAME}/items?expand=fields&$top=500"
    )
    headers = {"Authorization": f"Bearer {token}"}
    items, next_link = [], url

    while next_link:
        r = requests.get(next_link, headers=headers, timeout=15)
        r.raise_for_status()
        data      = r.json()
        items    += data.get("value", [])
        next_link = data.get("@odata.nextLink")

    return items


def sync_from_sharepoint(token: str) -> Dict[str, int]:
    """Import new SP list items into SQLite. Returns {imported, skipped}."""
    _ensure_sync_table()
    items    = fetch_sp_items(token)
    imported = 0
    skipped  = 0

    for item in items:
        sp_id  = item.get("id", "")
        fields = item.get("fields", {})

        if _already_synced(sp_id):
            skipped += 1
            continue

        title          = (fields.get("Title") or "").strip()
        waste_category = (fields.get("WasteCategory") or "").strip()
        process_path   = (fields.get("ProcessPath") or "General").strip()
        observed_by    = (fields.get("ObserverName") or "Floor Leader").strip()
        severity       = (fields.get("Severity") or "Medium").strip()
        description    = (fields.get("Details") or "").strip()
        initial_comment= (fields.get("Comments") or "").strip()

        # Validate required fields
        if not title or waste_category not in (
            "Transportation","Inventory","Motion","Waiting",
            "Overproduction","Over-processing","Defects"
        ):
            log.warning("Skipping SP item %s — missing/invalid fields", sp_id)
            skipped += 1
            continue

        if severity not in ("Low", "Medium", "High", "Critical"):
            severity = "Medium"

        obs_id = quick_log_observation(
            process_path    = process_path or "SharePoint Import",
            waste_category  = waste_category,
            title           = title,
            description     = description,
            severity        = severity,
            observed_by     = observed_by,
            initial_comment = initial_comment,
        )
        _record_sync(sp_id, obs_id)
        imported += 1

    return {"imported": imported, "skipped": skipped, "total": len(items)}
