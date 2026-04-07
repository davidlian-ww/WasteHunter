"""Main FastAPI application for TIMWOOD Waste Dashboard"""
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
    get_path_details, WASTE_CATEGORIES
)

app = FastAPI(title="TIMWOOD Waste Dashboard")
templates = Jinja2Templates(directory="app/templates")

# Initialize database on startup
@app.on_event("startup")
async def startup():
    init_db()


# Dashboard - Home
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = get_dashboard_stats()
    sites = get_all_sites()
    paths = get_process_paths()
    observations = get_waste_observations()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "sites": sites,
        "paths": paths,
        "observations": observations,
        "waste_categories": WASTE_CATEGORIES
    })


# Sites Management
@app.get("/sites", response_class=HTMLResponse)
async def sites_list(request: Request):
    sites = get_all_sites()
    return templates.TemplateResponse("sites.html", {
        "request": request,
        "sites": sites
    })


@app.post("/sites/create", response_class=HTMLResponse)
async def sites_create(
    request: Request,
    name: str = Form(...),
    code: str = Form(...),
    location: str = Form(""),
    site_type: str = Form("FC")
):
    try:
        create_site(name, code, location, site_type)
        sites = get_all_sites()
        return templates.TemplateResponse("components/sites_list.html", {
            "request": request,
            "sites": sites
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Process Paths
@app.get("/paths", response_class=HTMLResponse)
async def paths_list(request: Request, site_id: Optional[int] = None):
    sites = get_all_sites()
    paths = get_process_paths(site_id)
    return templates.TemplateResponse("paths.html", {
        "request": request,
        "sites": sites,
        "paths": paths,
        "selected_site_id": site_id
    })


@app.post("/paths/create", response_class=HTMLResponse)
async def paths_create(
    request: Request,
    site_id: int = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    created_by: str = Form("User")
):
    path_id = create_process_path(site_id, name, description, created_by)
    return RedirectResponse(url=f"/paths/{path_id}", status_code=303)


@app.get("/paths/{path_id}", response_class=HTMLResponse)
async def path_detail(request: Request, path_id: int):
    path = get_path_details(path_id)
    if not path:
        raise HTTPException(status_code=404, detail="Process path not found")
    
    return templates.TemplateResponse("path_detail.html", {
        "request": request,
        "path": path,
        "waste_categories": WASTE_CATEGORIES
    })


# Process Steps
@app.post("/paths/{path_id}/steps", response_class=HTMLResponse)
async def add_step(
    request: Request,
    path_id: int,
    name: str = Form(...),
    description: str = Form("")
):
    add_process_step(path_id, name, description)
    path = get_path_details(path_id)
    return templates.TemplateResponse("components/steps_list.html", {
        "request": request,
        "steps": path['steps'],
        "path_id": path_id,
        "waste_categories": WASTE_CATEGORIES
    })


# Waste Observations
@app.post("/observations/create", response_class=HTMLResponse)
async def create_observation(
    request: Request,
    step_id: int = Form(...),
    waste_category: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    severity: str = Form("Medium"),
    observed_by: str = Form("User")
):
    obs_id = create_waste_observation(
        step_id, waste_category, title, description, severity, observed_by
    )
    observations = get_waste_observations(step_id=step_id)
    return templates.TemplateResponse("components/observations_list.html", {
        "request": request,
        "observations": observations,
        "step_id": step_id
    })


@app.get("/observations/{obs_id}", response_class=HTMLResponse)
async def observation_detail(request: Request, obs_id: int):
    observations = get_waste_observations()
    observation = next((o for o in observations if o['id'] == obs_id), None)
    if not observation:
        raise HTTPException(status_code=404, detail="Observation not found")
    
    comments = get_comments(obs_id)
    return templates.TemplateResponse("observation_detail.html", {
        "request": request,
        "observation": observation,
        "comments": comments
    })


@app.post("/observations/{obs_id}/status", response_class=HTMLResponse)
async def update_status(
    request: Request,
    obs_id: int,
    status: str = Form(...)
):
    update_observation_status(obs_id, status)
    observations = get_waste_observations()
    observation = next((o for o in observations if o['id'] == obs_id), None)
    return templates.TemplateResponse("components/observation_card.html", {
        "request": request,
        "observation": observation
    })


# Comments
@app.post("/observations/{obs_id}/comments", response_class=HTMLResponse)
async def add_observation_comment(
    request: Request,
    obs_id: int,
    author: str = Form(...),
    comment: str = Form(...)
):
    add_comment(obs_id, author, comment)
    comments = get_comments(obs_id)
    return templates.TemplateResponse("components/comments_list.html", {
        "request": request,
        "comments": comments,
        "obs_id": obs_id
    })


# API Endpoints for HTMX
@app.get("/api/stats", response_class=HTMLResponse)
async def stats_api(request: Request):
    stats = get_dashboard_stats()
    return templates.TemplateResponse("components/stats_cards.html", {
        "request": request,
        "stats": stats
    })


@app.get("/api/observations/filter", response_class=HTMLResponse)
async def filter_observations(
    request: Request,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None
):
    observations = get_waste_observations()
    
    # Filter observations
    if category:
        observations = [o for o in observations if o['waste_category'] == category]
    if severity:
        observations = [o for o in observations if o['severity'] == severity]
    if status:
        observations = [o for o in observations if o['status'] == status]
    
    return templates.TemplateResponse("components/observations_table.html", {
        "request": request,
        "observations": observations
    })
