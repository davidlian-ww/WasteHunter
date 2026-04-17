"""Main FastAPI application for TIMWOOD Waste Dashboard with FMA Analysis"""
from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import csv
import io as _io
import json
import socket
import base64
import io
import qrcode
import threading
from app.ns_seeder import seed_ns_sites

from app.sharepoint_sync import (
    sync_from_sharepoint, sync_from_teams, import_from_json_export,
    get_access_token, DeviceCodeRequired,
    SHAREPOINT_FORM_URL,
)

# In-memory sync state (reset on server restart)
_sync_state: dict = {
    "status":      "idle",   # idle | needs_auth | syncing | done | error
    "device_msg":  None,     # shown to user when device-code needed
    "device_flow": None,     # the msal flow object
    "last_sync":   None,
    "last_result": None,
}
from app.database import (
    init_db, get_all_sites, create_site, get_process_paths,
    create_process_path, get_process_steps, add_process_step,
    get_waste_observations, create_waste_observation, get_comments,
    add_comment, get_dashboard_stats, update_observation_status,
    get_path_details, WASTE_CATEGORIES, create_failure_mode, get_failure_mode,
    update_failure_mode, calculate_rpn, get_fma_analytics,
    quick_log_observation, get_all_process_path_names, get_recent_observations,
    import_from_forms_csv, upsert_pwa_observation, get_pwa_observations,
    start_study, get_study, get_study_observations, log_fmo_in_study, end_study,
    get_all_studies, get_studies_stats,
    get_bank_observations, get_bank_stats,
)

app = FastAPI(title="TIMWOOD Failure Mode Analysis Dashboard")

# Allow the atlas-fmo PWA (any origin on Eagle WiFi) to POST observations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
async def startup():
    init_db()
    seed_ns_sites()


@app.get("/health")
async def health():
    return {"status": "OK"}


# ── PWA SYNC ENDPOINTS ───────────────────────────────────────────

class PWAObservation(BaseModel):
    id: int
    observer: str = "Anonymous"
    site: str = ""
    shift: str = ""
    process_path: str = ""
    observer_area: str = ""
    waste_category: str
    title: str
    description: str = ""
    severity: str = "Medium"
    timestamp: str
    observation_duration_seconds: Optional[int] = None


@app.post("/api/pwa/observations")
async def receive_pwa_observation(obs: PWAObservation):
    """Receives one observation from the atlas-fmo PWA.
    Idempotent — safe to retry on network failure.
    """
    is_new = upsert_pwa_observation(obs.model_dump())
    return {"ok": True, "new": is_new, "id": obs.id}


@app.get("/api/pwa/observations")
async def fetch_pwa_observations(
    site: Optional[str] = None,
    limit: int = 1000,
):
    """Returns all synced PWA observations, newest first.
    Optionally filter by site code (e.g. ?site=IND2).
    """
    return get_pwa_observations(site=site, limit=limit)



def _lan_ip() -> str:
    """Best-effort LAN IP — falls back to localhost."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _make_qr_b64(url: str) -> str:
    """Generate QR code PNG and return as base64 data URI.
    Black on white = maximum camera compatibility.
    """
    qr = qrcode.QRCode(
        box_size=10,   # bigger = easier to scan
        border=4,      # standard quiet zone (4 modules)
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # 30% damage tolerance
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ── SHARE PAGE ───────────────────────────────────────────────────
_ATLAS_PWA_URL = "https://puppy.walmart.com/sharing/d0l0ka3/atlas-fmo-audit-tool"

@app.get("/share", response_class=HTMLResponse)
async def share_page(request: Request):
    """Shareable QR page — Atlas PWA + local server + SharePoint form."""
    ip  = _lan_ip()
    url = f"http://{ip}:8001"
    return templates.TemplateResponse(request, "share.html", {
        "url":         url,
        "ip":          ip,
        "qr_b64":      _make_qr_b64(url),
        "sp_url":      SHAREPOINT_FORM_URL,
        "sp_qr_b64":   _make_qr_b64(SHAREPOINT_FORM_URL),
        "atlas_url":   _ATLAS_PWA_URL,
        "atlas_qr_b64": _make_qr_b64(_ATLAS_PWA_URL),
    })


# ── MAIN DASHBOARD ────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard — log form + live observation feed."""
    stats = get_dashboard_stats()
    return templates.TemplateResponse(request, "fma_dashboard.html", {
        "waste_categories": WASTE_CATEGORIES,
        "path_names": get_all_process_path_names(),
        "observations": get_recent_observations(),
        "total_observations": stats["total_observations"],
        "open_observations": stats["open_observations"],
        "total_paths": stats["total_paths"],
    })


# ── QUICK LOG (main entry point for new FMOs) ─────────────────────
@app.post("/quick-log", response_class=HTMLResponse)
async def quick_log(
    request: Request,
    process_path: str = Form(...),
    waste_category: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    severity: str = Form("Medium"),
    observed_by: str = Form("Anonymous"),
    initial_comment: str = Form(""),
    observation_duration_seconds: Optional[int] = Form(None),
):
    """Create one FMO and return the refreshed feed + updated stats."""
    quick_log_observation(
        process_path=process_path,
        waste_category=waste_category,
        title=title,
        description=description,
        severity=severity,
        observed_by=observed_by,
        initial_comment=initial_comment,
        observation_duration_seconds=observation_duration_seconds,
    )
    stats = get_dashboard_stats()
    return templates.TemplateResponse(request, "components/observations_feed.html", {
        "observations": get_recent_observations(),
        "path_names": get_all_process_path_names(),
        "total_observations": stats["total_observations"],
        "open_observations": stats["open_observations"],
        "total_paths": stats["total_paths"],
    })


# ── OBSERVATIONS FEED (HTMX partial) ──────────────────────────────
@app.get("/api/feed", response_class=HTMLResponse)
async def feed(request: Request):
    """Return the live feed partial for polling / manual refresh."""
    stats = get_dashboard_stats()
    return templates.TemplateResponse(request, "components/observations_feed.html", {
        "observations": get_recent_observations(),
        "path_names": get_all_process_path_names(),
        "total_observations": stats["total_observations"],
        "open_observations": stats["open_observations"],
        "total_paths": stats["total_paths"],
    })


# ── PROCESS PATH NAMES (datalist autocomplete) ────────────────────
@app.get("/api/paths/names", response_class=HTMLResponse)
async def path_names(request: Request):
    """Return <option> tags for datalist autocomplete."""
    names = get_all_process_path_names()
    html = "".join(f'<option value="{n}">' for n in names)
    return HTMLResponse(html)


# ── FMA ANALYTICS PAGE ────────────────────────────────────────────
@app.get("/fma", response_class=HTMLResponse)
async def fma_analytics_page(request: Request):
    """Comprehensive FMA analysis page"""
    fma_data = get_fma_analytics()

    ctx = {
        "fma_data": fma_data,
        "top_by_rpn_json": json.dumps(fma_data["top_by_rpn"], default=str),
        "by_category_json": json.dumps(fma_data["by_category"], default=str),
        "severity_dist_json": json.dumps(fma_data["severity_dist"], default=str),
        "mitigation_status_json": json.dumps(fma_data["mitigation_status"], default=str),
        "waste_categories": WASTE_CATEGORIES,
    }

    return templates.TemplateResponse(request, "fma_analytics.html", ctx)


# ── SITES ────────────────────────────────────────────────────────
@app.get("/sites", response_class=HTMLResponse)
async def sites_list(request: Request):
    return templates.TemplateResponse(request, "sites.html", {
        "sites": get_all_sites(),
    })


@app.post("/sites/create", response_class=HTMLResponse)
async def sites_create(
    request: Request,
    name: str = Form(...),
    code: str = Form(...),
    location: str = Form(""),
    site_type: str = Form("FC"),
):
    create_site(name, code, location, site_type)
    return templates.TemplateResponse(request, "components/sites_list.html", {
        "sites": get_all_sites(),
    })


# ── PROCESS PATHS ────────────────────────────────────────────────
@app.get("/paths", response_class=HTMLResponse)
async def paths_list(request: Request, site_id: Optional[int] = None):
    return templates.TemplateResponse(request, "paths.html", {
        "sites": get_all_sites(),
        "paths": get_process_paths(site_id),
        "selected_site_id": site_id,
    })


@app.post("/paths/create", response_class=HTMLResponse)
async def paths_create(
    request: Request,
    site_id: int = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    created_by: str = Form("User"),
):
    path_id = create_process_path(site_id, name, description, created_by)
    return RedirectResponse(url=f"/paths/{path_id}", status_code=303)


@app.get("/paths/{path_id}", response_class=HTMLResponse)
async def path_detail(request: Request, path_id: int):
    path = get_path_details(path_id)
    if not path:
        raise HTTPException(status_code=404, detail="Process path not found")
    return templates.TemplateResponse(request, "path_detail.html", {
        "path": path,
        "waste_categories": WASTE_CATEGORIES,
    })


# ── PROCESS STEPS ────────────────────────────────────────────────
@app.post("/paths/{path_id}/steps", response_class=HTMLResponse)
async def add_step(
    request: Request,
    path_id: int,
    name: str = Form(...),
    description: str = Form(""),
):
    add_process_step(path_id, name, description)
    path = get_path_details(path_id)
    return templates.TemplateResponse(request, "components/steps_list.html", {
        "steps": path["steps"],
        "path_id": path_id,
        "waste_categories": WASTE_CATEGORIES,
    })


# ── WASTE OBSERVATIONS ───────────────────────────────────────────
@app.post("/observations/create", response_class=HTMLResponse)
async def create_observation(
    request: Request,
    step_id: int = Form(...),
    waste_category: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    severity: str = Form("Medium"),
    observed_by: str = Form("User"),
):
    obs_id = create_waste_observation(
        step_id, waste_category, title, description, severity, observed_by
    )
    # Auto-create FMA record
    create_failure_mode(obs_id)

    return templates.TemplateResponse(request, "components/observations_list.html", {
        "observations": get_waste_observations(step_id=step_id),
        "step_id": step_id,
    })


@app.get("/observations/{obs_id}", response_class=HTMLResponse)
async def observation_detail(request: Request, obs_id: int):
    observations = get_waste_observations()
    observation = next((o for o in observations if o["id"] == obs_id), None)
    if not observation:
        raise HTTPException(status_code=404, detail="Observation not found")

    failure_mode = get_failure_mode(obs_id)
    rpn = None
    if failure_mode:
        if failure_mode.get("occurrence_score") and failure_mode.get("detection_score"):
            rpn = calculate_rpn(
                observation["severity"],
                failure_mode["occurrence_score"],
                failure_mode["detection_score"]
            )

    return templates.TemplateResponse(request, "observation_detail.html", {
        "observation": observation,
        "failure_mode": failure_mode,
        "rpn": rpn,
        "comments": get_comments(obs_id),
    })


@app.post("/observations/{obs_id}/status", response_class=HTMLResponse)
async def update_status(
    request: Request,
    obs_id: int,
    status: str = Form(...),
):
    update_observation_status(obs_id, status)
    observations = get_waste_observations()
    observation = next((o for o in observations if o["id"] == obs_id), None)
    return templates.TemplateResponse(request, "components/observation_card.html", {
        "observation": observation,
    })


# ── FAILURE MODE ANALYSIS ────────────────────────────────────────
@app.post("/fma/{obs_id}/update", response_class=HTMLResponse)
async def update_fma(
    request: Request,
    obs_id: int,
    occurrence_score: int = Form(...),
    detection_score: int = Form(...),
    root_cause: str = Form(""),
    impact_hours: float = Form(0),
    impact_cost: float = Form(0),
    mitigation_action: str = Form(""),
    mitigation_owner: str = Form(""),
    mitigation_due_date: str = Form(""),
):
    observations = get_waste_observations()
    observation = next((o for o in observations if o["id"] == obs_id), None)

    rpn = calculate_rpn(observation["severity"], occurrence_score, detection_score)

    update_failure_mode(
        obs_id,
        occurrence_score=occurrence_score,
        detection_score=detection_score,
        root_cause=root_cause,
        rpn_score=rpn,
        impact_hours=impact_hours,
        impact_cost=impact_cost,
        mitigation_action=mitigation_action,
        mitigation_owner=mitigation_owner,
        mitigation_due_date=mitigation_due_date,
    )

    fm = get_failure_mode(obs_id)
    return templates.TemplateResponse(request, "components/failure_mode_card.html", {
        "failure_mode": fm,
        "rpn": rpn,
        "obs_id": obs_id,
    })


@app.post("/fma/{obs_id}/mitigation", response_class=HTMLResponse)
async def update_mitigation(
    request: Request,
    obs_id: int,
    mitigation_status: str = Form(...),
):
    update_failure_mode(obs_id, mitigation_status=mitigation_status)
    fm = get_failure_mode(obs_id)
    return templates.TemplateResponse(request, "components/mitigation_status.html", {
        "failure_mode": fm,
    })


# ── CSV IMPORT (Microsoft Forms export) ───────────────────────────────
@app.post("/import-csv", response_class=HTMLResponse)
async def import_csv(request: Request, file: UploadFile = File(...)):
    """Accept a Microsoft Forms CSV export and bulk-import all rows."""
    if not file.filename.endswith(".csv"):
        return HTMLResponse(
            '<div class="text-red-600 text-sm font-semibold">Please upload a .csv file.</div>',
            status_code=400,
        )
    csv_bytes = await file.read()
    imported, skipped, errors = import_from_forms_csv(csv_bytes)
    stats = get_dashboard_stats()
    return templates.TemplateResponse(request, "components/import_result.html", {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "observations": get_recent_observations(),
        "path_names": get_all_process_path_names(),
        "total_observations": stats["total_observations"],
        "open_observations": stats["open_observations"],
        "total_paths": stats["total_paths"],
    })


# ── SHAREPOINT SYNC ───────────────────────────────────────────────
@app.get("/sync/sharepoint", response_class=JSONResponse)
async def sync_sharepoint():
    """Sync FMO Observations from SharePoint list into SQLite.
    First call may return a device-code challenge if not yet authenticated.
    """
    global _sync_state
    if _sync_state["status"] == "syncing":
        return JSONResponse({"status": "syncing", "message": "Sync already in progress…"})

    # Try silent token first
    try:
        token = get_access_token()
    except DeviceCodeRequired as dcr:
        _sync_state.update({
            "status":      "needs_auth",
            "device_msg":  dcr.message,
            "device_flow": dcr,
        })
        return JSONResponse({
            "status":  "needs_auth",
            "message": dcr.message,
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

    if not token:
        return JSONResponse({"status": "error", "message": "Could not acquire token."}, status_code=500)

    _sync_state["status"] = "syncing"
    try:
        result = sync_from_sharepoint(token)
        _sync_state.update({
            "status":      "done",
            "last_sync":   datetime.now().strftime("%Y-%m-%d %H:%M"),
            "last_result": result,
        })
        return JSONResponse({"status": "done", **result})
    except Exception as e:
        _sync_state.update({"status": "error", "last_result": str(e)})
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/sync/complete", response_class=JSONResponse)
async def complete_sharepoint_auth():
    """Call after user has completed the device-code sign-in. Finishes auth and syncs."""
    global _sync_state
    if _sync_state["status"] != "needs_auth" or not _sync_state.get("device_flow"):
        return JSONResponse({"status": "error", "message": "No pending auth. Trigger /sync/sharepoint first."})

    def _do_auth_and_sync():
        global _sync_state
        try:
            dcr: DeviceCodeRequired = _sync_state["device_flow"]
            token = dcr.complete()  # blocks until signed in
            if not token:
                _sync_state.update({"status": "error", "last_result": "Auth failed — no token returned."})
                return
            result = sync_from_sharepoint(token)
            _sync_state.update({
                "status":      "done",
                "last_sync":   datetime.now().strftime("%Y-%m-%d %H:%M"),
                "last_result": result,
                "device_msg":  None,
                "device_flow": None,
            })
        except Exception as e:
            _sync_state.update({"status": "error", "last_result": str(e)})

    t = threading.Thread(target=_do_auth_and_sync, daemon=True)
    t.start()
    _sync_state["status"] = "syncing"
    return JSONResponse({"status": "syncing", "message": "Auth completing in background. Sync will run automatically."})


@app.get("/sync/status", response_class=JSONResponse)
async def sync_status():
    return JSONResponse({
        "status":      _sync_state["status"],
        "last_sync":   _sync_state["last_sync"],
        "last_result": _sync_state["last_result"],
        "sp_form_url": SHAREPOINT_FORM_URL,
    })

# ── TEAMS CHANNEL SYNC ────────────────────────────────────────────
@app.get("/sync/teams", response_class=JSONResponse)
async def sync_teams():
    """Pull FMO_JSON submissions from IND2 Quality Channel into SQLite."""
    global _sync_state
    try:
        token = get_access_token()
    except DeviceCodeRequired as dcr:
        _sync_state.update({"status": "needs_auth", "device_msg": dcr.message, "device_flow": dcr})
        return JSONResponse({"status": "needs_auth", "message": dcr.message})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    if not token:
        return JSONResponse({"status": "error", "message": "No token"}, status_code=500)
    try:
        result = sync_from_teams(token)
        return JSONResponse({"status": "done", **result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ── ATLAS PWA JSON IMPORT ─────────────────────────────────────────
@app.post("/import-json", response_class=HTMLResponse)
async def import_json(request: Request, file: UploadFile = File(...)):
    """Import a JSON export file from the Atlas FMO PWA."""
    if not file.filename.lower().endswith(".json"):
        return HTMLResponse('<div class="text-red-600 text-sm font-semibold">Please upload a .json file.</div>', status_code=400)
    raw = await file.read()
    try:
        result = import_from_json_export(raw)
    except ValueError as e:
        return HTMLResponse(f'<div class="text-red-600 text-sm font-semibold">{e}</div>', status_code=400)
    stats = get_dashboard_stats()
    return templates.TemplateResponse(request, "components/import_result.html", {
        "imported": result["imported"],
        "skipped":  result["skipped"],
        "errors":   [],
        "observations":      get_recent_observations(),
        "path_names":        get_all_process_path_names(),
        "total_observations": stats["total_observations"],
        "open_observations":  stats["open_observations"],
        "total_paths":        stats["total_paths"],
    })


# ── COMMENTS ────────────────────────────────────────────
@app.post("/observations/{obs_id}/comments", response_class=HTMLResponse)
async def add_observation_comment(
    request: Request,
    obs_id: int,
    author: str = Form(...),
    comment: str = Form(...),
):
    add_comment(obs_id, author, comment)
    return templates.TemplateResponse(request, "components/inline_comments.html", {
        "comments": get_comments(obs_id),
        "obs_id": obs_id,
    })


# ── API ENDPOINTS FOR CHARTS ──────────────────────────────────────
@app.get("/api/stats", response_class=HTMLResponse)
async def stats_api(request: Request):
    return templates.TemplateResponse(request, "components/stats_cards.html", {
        "stats": get_dashboard_stats(),
    })


@app.get("/api/observations/filter", response_class=HTMLResponse)
async def filter_observations(
    request: Request,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
):
    observations = get_waste_observations()
    if category:
        observations = [o for o in observations if o["waste_category"] == category]
    if severity:
        observations = [o for o in observations if o["severity"] == severity]
    if status:
        observations = [o for o in observations if o["status"] == status]
    return templates.TemplateResponse(request, "components/observations_table.html", {
        "observations": observations,
    })


@app.get("/api/fma-data")
async def get_fma_data():
    """API endpoint for FMA analytics data"""
    return get_fma_analytics()


# ── DATA BANK ROUTES ─────────────────────────────────────────────────────────

@app.get("/bank", response_class=HTMLResponse)
async def bank_page(
    request:   Request,
    source:    Optional[str] = None,
    path:      Optional[str] = None,
    category:  Optional[str] = None,
    q:         Optional[str] = None,
    date_from: Optional[str] = None,
    date_to:   Optional[str] = None,
):
    """Data Bank — browse, upload, and manually enter historical observations."""
    obs   = get_bank_observations(
        source=source, path=path, category=category,
        q=q, date_from=date_from, date_to=date_to,
    )
    stats = get_bank_stats()
    paths = get_all_process_path_names()
    return templates.TemplateResponse(request, "bank.html", {
        "observations": obs,
        "stats":        stats,
        "paths":        paths,
        "f_source":     source   or "",
        "f_path":       path     or "",
        "f_category":   category or "",
        "f_q":          q        or "",
        "f_date_from":  date_from or "",
        "f_date_to":    date_to  or "",
        "waste_categories": [
            "Transportation","Inventory","Motion","Waiting",
            "Overproduction","Over-processing","Defects","Safety",
        ],
    })


@app.post("/bank/upload", response_class=HTMLResponse)
async def bank_upload(request: Request, file: UploadFile = File(...)):
    """CSV upload to the data bank — source tagged as 'csv-import'."""
    if not file.filename.lower().endswith(".csv"):
        return HTMLResponse(
            '<p class="text-red-600 font-semibold">Only .csv files are accepted.</p>',
            status_code=400,
        )
    csv_bytes = await file.read()
    imported, skipped, errors = import_from_forms_csv(csv_bytes)
    stats = get_bank_stats()
    return templates.TemplateResponse(request, "components/bank_upload_result.html", {
        "imported": imported,
        "skipped":  skipped,
        "errors":   errors,
        "stats":    stats,
    })


@app.post("/bank/manual", response_class=HTMLResponse)
async def bank_manual(
    request:       Request,
    process_path:  str          = Form(...),
    waste_category: str         = Form(...),
    title:         str          = Form(...),
    description:   str          = Form(""),
    severity:      str          = Form("Medium"),
    observed_by:   str          = Form("Anonymous"),
    observed_at:   str          = Form(""),
):
    """Manual back-dated entry into the data bank."""
    ts = observed_at.replace("T", " ") if observed_at else None
    quick_log_observation(
        process_path=process_path,
        waste_category=waste_category,
        title=title.strip(),
        description=description.strip(),
        severity=severity,
        observed_by=observed_by.strip() or "Anonymous",
        observed_at=ts,
        source="manual-import",
    )
    obs   = get_bank_observations()
    stats = get_bank_stats()
    return templates.TemplateResponse(request, "components/bank_upload_result.html", {
        "imported": 1,
        "skipped":  0,
        "errors":   [],
        "stats":    stats,
    })


@app.get("/bank/export")
async def bank_export(
    source:    Optional[str] = None,
    path:      Optional[str] = None,
    category:  Optional[str] = None,
    date_from: Optional[str] = None,
    date_to:   Optional[str] = None,
):
    """Download the current bank view as a CSV file."""
    obs = get_bank_observations(
        source=source, path=path, category=category,
        date_from=date_from, date_to=date_to, limit=100_000,
    )
    buf = _io.StringIO()
    fields = ["id","path_name","waste_category","title","description",
              "severity","status","observed_by","observed_at","source"]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(obs)
    return HTMLResponse(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="bank_export.csv"'},
    )


# ── STUDY SESSION ROUTES ──────────────────────────────────────────────────────

@app.get("/studies", response_class=HTMLResponse)
async def studies_list(request: Request,
                        status: Optional[str] = None,
                        path: Optional[str] = None,
                        observer: Optional[str] = None):
    """All FMO study sessions from all users, filterable."""
    studies  = get_all_studies(status=status, path_name=path, observer=observer)
    agg      = get_studies_stats()
    return templates.TemplateResponse(request, "studies.html", {
        "studies":  studies,
        "agg":      agg,
        "filter_status":   status   or "",
        "filter_path":     path     or "",
        "filter_observer": observer or "",
    })


@app.post("/study/start", response_class=HTMLResponse)
async def study_start(
    request: Request,
    path_id: int = Form(...),
    path_name: str = Form(...),
    site_name: str = Form(""),
    observer: str = Form("Anonymous"),
):
    """Create a new study session and redirect to the active study page."""
    session_id = start_study(
        path_name=path_name,
        observer=observer,
        path_id=path_id,
        site_name=site_name,
    )
    return RedirectResponse(f"/study/{session_id}", status_code=303)


@app.get("/study/{session_id}", response_class=HTMLResponse)
async def study_active(request: Request, session_id: int):
    """Active study workspace — log FMOs with timed observations."""
    session = get_study(session_id)
    if not session or session["status"] != "active":
        return RedirectResponse("/paths", status_code=303)
    observations = get_study_observations(session_id)
    total_waste = sum(
        o["observation_duration_seconds"] or 0 for o in observations
    )
    return templates.TemplateResponse(request, "study_active.html", {
        "session":         session,
        "waste_categories": WASTE_CATEGORIES,
        "observations":    observations,
        "total_waste_seconds": total_waste,
    })


@app.post("/study/{session_id}/log", response_class=HTMLResponse)
async def study_log_fmo(
    request: Request,
    session_id: int,
    waste_category: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    severity: str = Form("Medium"),
    observed_by: str = Form("Anonymous"),
    observation_duration_seconds: Optional[int] = Form(None),
):
    """Log one FMO inside an active study and return the refreshed obs list."""
    session = get_study(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Study session not found")
    log_fmo_in_study(
        session_id=session_id,
        process_path=session["path_name"],
        waste_category=waste_category,
        title=title,
        description=description,
        severity=severity,
        observed_by=observed_by,
        observation_duration_seconds=observation_duration_seconds,
    )
    observations = get_study_observations(session_id)
    total_waste = sum(o["observation_duration_seconds"] or 0 for o in observations)
    return templates.TemplateResponse(request, "components/study_obs_list.html", {
        "observations": observations,
        "total_waste_seconds": total_waste,
        "session_id": session_id,
    })


@app.post("/study/{session_id}/end")
async def study_end(session_id: int):
    """End the study, compute totals, redirect to summary."""
    session = get_study(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Study session not found")
    end_study(session_id)
    return RedirectResponse(f"/study/{session_id}/summary", status_code=303)


@app.get("/study/{session_id}/summary", response_class=HTMLResponse)
async def study_summary_page(request: Request, session_id: int):
    """Post-study summary report — wall time, total waste time, FMO breakdown."""
    session = get_study(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Study session not found")
    observations = get_study_observations(session_id)

    # Build per-category totals for Chart.js
    cat_totals: dict = {}
    for obs in observations:
        cat = obs["waste_category"]
        dur = obs["observation_duration_seconds"] or 0
        if cat not in cat_totals:
            cat_totals[cat] = {"count": 0, "secs": 0}
        cat_totals[cat]["count"] += 1
        cat_totals[cat]["secs"]  += dur

    # Sort by time descending for the chart
    sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1]["secs"], reverse=True)

    cat_chart_json = json.dumps({
        "labels": [c for c, _ in sorted_cats],
        "times":  [v["secs"] for _, v in sorted_cats],
        "counts": [v["count"] for _, v in sorted_cats],
        "colors": [
            {"Transportation":"#dc2626","Inventory":"#ea580c","Motion":"#ca8a04",
             "Waiting":"#0053e2","Overproduction":"#7c3aed","Over-processing":"#0891b2",
             "Defects":"#dc2626","Safety":"#2a8703"}.get(c, "#6b7280")
            for c, _ in sorted_cats
        ],
    })
    total_waste = session.get("total_waste_seconds") or 0

    return templates.TemplateResponse(request, "study_summary.html", {
        "session":         session,
        "observations":    observations,
        "sorted_cats":     sorted_cats,
        "total_waste":     total_waste,
        "cat_chart_json":  cat_chart_json,
    })
