"""Main FastAPI application for TIMWOOD Waste Dashboard with FMA Analysis"""
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
import json

from app.database import (
    init_db, get_all_sites, create_site, get_process_paths,
    create_process_path, get_process_steps, add_process_step,
    get_waste_observations, create_waste_observation, get_comments,
    add_comment, get_dashboard_stats, update_observation_status,
    get_path_details, WASTE_CATEGORIES, create_failure_mode, get_failure_mode,
    update_failure_mode, calculate_rpn, get_fma_analytics
)

app = FastAPI(title="TIMWOOD Failure Mode Analysis Dashboard")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/health")
async def health():
    return {"status": "OK"}


# ── MAIN DASHBOARD ────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard with FMA analytics"""
    stats = get_dashboard_stats()
    fma_analytics = get_fma_analytics()

    ctx = {
        "total_sites": stats["total_sites"],
        "total_paths": stats["total_paths"],
        "total_observations": stats["total_observations"],
        "open_observations": stats["open_observations"],
        "waste_by_category_json": json.dumps(stats["waste_by_category"]),
        "severity_breakdown_json": json.dumps(stats["severity_breakdown"]),
        "category_chart_json": json.dumps(fma_analytics["by_category"]),
        "severity_dist_json": json.dumps(fma_analytics["severity_dist"]),
        "fma_analytics": fma_analytics,
    }

    return templates.TemplateResponse(request, "fma_dashboard.html", ctx)


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


# ── COMMENTS ─────────────────────────────────────────────────────
@app.post("/observations/{obs_id}/comments", response_class=HTMLResponse)
async def add_observation_comment(
    request: Request,
    obs_id: int,
    author: str = Form(...),
    comment: str = Form(...),
):
    add_comment(obs_id, author, comment)
    return templates.TemplateResponse(request, "components/comments_list.html", {
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
