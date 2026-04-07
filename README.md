# TIMWOOD Waste Dashboard 🗑️

An interactive web application for conducting TIMWOOD 7 Waste Studies in NS Fulfillment Centers.

## What is TIMWOOD?

The 7 Wastes in Lean Manufacturing:
- **T**ransportation - Unnecessary movement of products
- **I**nventory - Excess products not being processed
- **M**otion - Unnecessary movement of people/equipment
- **W**aiting - Idle time without productivity
- **O**verproduction - Producing more than needed
- **O**ver-processing - More work than required
- **D**efects - Errors, rework, or quality issues

## Features

✨ **Site Management** - Create and manage NS FCs
🛤️ **Process Path Builder** - Build custom process flows with multiple steps
📊 **Waste Tracking** - Log waste observations under any TIMWOOD category
💬 **Collaborative Comments** - Discuss and track progress on each observation
📈 **Real-time Dashboard** - Live stats and analytics
🎨 **Walmart Themed** - Full Walmart color scheme and WCAG 2.2 Level AA compliance

## Quick Start

### Installation

```bash
# Create virtual environment
uv venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt --index-url https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple --allow-insecure-host pypi.ci.artifacts.walmart.com
```

### Run

```bash
python run.py
```

The app will be available at: **http://localhost:8000**

## Usage Guide

### 1. Create a Site
- Navigate to "Sites" in the nav
- Click "+ Add New Site"
- Enter FC name, code, and location
- Submit to create

### 2. Build a Process Path
- Go to "Process Paths"
- Click "+ Create Process Path"
- Select the site and name your process
- Add steps one by one to build the flow

### 3. Track Waste
- Open a process path
- For each step, click "+ Report Waste"
- Select the TIMWOOD category
- Fill in details about the waste
- Set severity level
- Submit observation

### 4. Collaborate
- Click on any observation to view details
- Add comments to discuss solutions
- Update status as you make progress
- Track resolution over time

## Tech Stack

- **Backend**: FastAPI + Python 3.9+
- **Database**: SQLite (embedded, zero-config)
- **Frontend**: HTMX + Tailwind CSS
- **Theme**: Walmart Design System colors

## Database Schema

- **sites** - FC locations
- **process_paths** - Process definitions
- **process_steps** - Individual steps in a path
- **waste_observations** - Logged waste instances
- **comments** - Discussion threads

## Contributing

Built with ❤️ for Walmart NS operations teams!

## Support

Questions? Join the Code Puppy community:
- Teams: https://teams.microsoft.com/l/channel/19%3AGbP8DGJjrXq1sL3IlXErZc5U7hk-IEqsokmnImcKyP41%40thread.tacv2/General
- Slack: https://walmart.enterprise.slack.com/archives/C094Y1D24JY
