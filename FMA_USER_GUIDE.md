# 🔧 TIMWOOD Failure Mode Analysis Dashboard

## Overview

This is an **enterprise-grade Failure Mode and Effects Analysis (FMEA)** tool designed for Walmart NS (Network & Supply) Fulfillment Centers. It combines TIMWOOD waste tracking with advanced failure mode analytics, including **RPN scoring**, **root cause analysis**, and **mitigation tracking**.

---

## ✨ Key Features

### 📊 Analytics & Dashboards
- **FMA Dashboard** - Executive summary with key metrics
- **Comprehensive Analytics** - Deep dive FMEA breakdown with charts
- **RPN Scoring** - Risk Priority Number calculation (Severity × Occurrence × Detection)
- **Category Analysis** - Failures segmented by TIMWOOD waste type
- **Mitigation Tracking** - Monitor progress on corrective actions

### 🎯 TIMWOOD Categories
- **T**ransportation - Unnecessary movement of products
- **I**nventory - Excess products not being processed
- **M**otion - Unnecessary movement of people/equipment
- **W**aiting - Idle time without productivity
- **O**verproduction - Producing more than needed
- **O**ver-processing - More work than required
- **D**efects - Errors, rework, or quality issues

### 💻 Technology Stack
- **Backend**: FastAPI + Python 3.9+
- **Database**: SQLite (embedded, zero-config)
- **Frontend**: HTMX + Tailwind CSS + Chart.js
- **Design**: Walmart Design System (WCAG 2.2 Level AA compliant)

---

## 🚀 Quick Start

### Installation

```bash
# Navigate to project directory
cd timwood-dashboard

# Install dependencies using uv
uv pip install -r requirements.txt --index-url https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple
```

### Run the Application

**Option 1: Using run.py**
```bash
python run.py
```

**Option 2: Using uvicorn directly**
```bash
uvicorn app.main:app --reload --port 8001
```

**Option 3: Using the batch file (Windows)**
```bash
start.bat
```

The app will be available at: **http://localhost:8001**

---

## 📖 User Guide

### 1. Dashboard Overview (Home Page)

**URL**: `http://localhost:8001/`

The main dashboard displays:
- **KPI Cards**: Total observations, open issues, sites, and process paths
- **Failure Distribution Charts**: Breakdown by TIMWOOD category
- **Severity Distribution**: Low/Medium/High/Critical breakdown
- **RPN Analysis**: Average Risk Priority Numbers by category
- **Status Overview**: Open/In Progress/Resolved/Closed distribution
- **Top 10 Failure Modes**: Ranked by RPN score with impacts
- **Executive Summary**: Total cost impact, hours lost, failures analyzed

### 2. Creating Sites

**Steps**:
1. Click "Manage Sites" or navigate to `/sites`
2. Click "+ Add New Site"
3. Fill in:
   - **FC Name**: e.g., "PHX2 Fulfillment Center"
   - **Code**: Short code, e.g., "PHX2"
   - **Location**: City/State
   - **Type**: Usually "FC" for fulfillment center
4. Click "Create Site"

### 3. Building Process Paths

**Steps**:
1. Go to "Create Paths" or navigate to `/paths`
2. Select a site from the dropdown
3. Click "+ Create Process Path"
4. Enter:
   - **Name**: Process name, e.g., "Inbound Receiving"
   - **Description**: What this process covers
   - **Created By**: Your name
5. Once created, add steps:
   - Click "Add Step"
   - Enter step name and description
   - Repeat for all steps in the process

**Example**: Inbound Receiving Process
- Dock doors open
- Pallet unloading
- Quality check
- Conveyor scanning
- Sortation

### 4. Logging Waste Observations

**Steps**:
1. Go to a process path detail page
2. Click "+ Report Waste" next to a step
3. Fill in:
   - **Waste Category**: Select from TIMWOOD list
   - **Title**: Brief title (e.g., "Pallet wait time at dock")
   - **Description**: Detailed description
   - **Severity**: Low/Medium/High/Critical
   - **Observed By**: Your name
4. Submit - an FMA record will auto-create

### 5. Analyzing Failure Modes (FMA)

Once an observation is logged, perform FMEA analysis:

1. **Navigate to Observation**: Click on any observation in the dashboard
2. **Complete FMA Form**:
   - **Occurrence Score** (1-10): How often does this occur?
     - 1 = Very rare (less than once per year)
     - 5 = Occasional (once per month)
     - 10 = Frequent (multiple times per day)
   
   - **Detection Score** (1-10): How easily is it detected?
     - 1 = Very obvious (detectable immediately)
     - 5 = Sometimes noticed (noticed after some time)
     - 10 = Hard to detect (only discovered through investigation)
   
   - **Root Cause**: Primary cause analysis
   - **Impact Hours**: Hours lost per occurrence
   - **Impact Cost**: Financial cost per occurrence
   
3. **Save** - RPN will auto-calculate as: `Severity × Occurrence × Detection`

4. **Add Mitigation**:
   - **Action**: What will be done to prevent this
   - **Owner**: Who is responsible
   - **Due Date**: Target completion date
   - **Status**: Not Started → In Progress → Completed

### 6. Using the FMA Analytics Page

**URL**: `http://localhost:8001/fma`

This comprehensive page includes:
- **Executive Summary**: Total failures, costs, hours, most common category
- **Category Breakdown**: Detailed breakdown by TIMWOOD type
- **RPN Rankings**: Top 10 failures by RPN score
- **Severity Distribution**: Color-coded severity analysis
- **Mitigation Progress**: Tracking of corrective actions
- **Key Insights**: AI-generated recommendations

---

## 📊 Understanding RPN Scores

### What is RPN?

**Risk Priority Number (RPN)** = **Severity × Occurrence × Detection**

### Severity Multipliers
- **Low** = 1
- **Medium** = 5
- **High** = 7
- **Critical** = 10

### Example Calculations

| Failure | Severity | Occurrence | Detection | RPN | Priority |
|---------|----------|-----------|-----------|-----|----------|
| Dock jam | High | 8 | 6 | 7 × 8 × 6 = **336** | 🔴 Critical |
| Slow scan | Medium | 5 | 3 | 5 × 5 × 3 = **75** | 🟡 Moderate |
| Label fading | Low | 2 | 8 | 1 × 2 × 8 = **16** | 🟢 Low |

**Action Guidelines**:
- **RPN > 200**: Immediate action required
- **RPN 100-200**: Schedule mitigation soon
- **RPN < 100**: Monitor and address as resources allow

---

## 💡 Best Practices

### 1. Regular Observations
- Log observations **as soon as they occur**
- Include specific details (date, time, impact)
- Don't wait to batch observations

### 2. RPN Analysis
- Focus mitigation efforts on **high RPN scores first**
- Use **Pareto principle** (80/20 rule) - 20% of failures cause 80% of impact
- Re-evaluate RPN after mitigation to track improvement

### 3. Root Cause Analysis
- Ask "Why?" 5 times to find true root cause
- Avoid treating symptoms instead of root causes
- Document the analysis process

### 4. Mitigation Tracking
- Assign owners and due dates
- Update status regularly
- Verify effectiveness after implementation
- Close only when verified

### 5. Collaboration
- Use comments to discuss observations
- Share updates on mitigation progress
- Document lessons learned

---

## 🛠️ Database Schema

### Tables

**sites**
- FC name, code, location, type, created_at

**process_paths**
- Site reference, name, description, created_by, created_at

**process_steps**
- Path reference, step_order, name, description

**waste_observations**
- Step reference, waste_category, title, description, severity, status, observed_by, observed_at

**failure_modes** (NEW!)
- Observation reference, occurrence_score, detection_score, root_cause, rpn_score
- impact_hours, impact_cost
- mitigation_action, mitigation_owner, mitigation_due_date, mitigation_status

**comments**
- Observation reference, author, comment, created_at

---

## 📈 Reports & Analytics

### Dashboard Metrics

**Home Dashboard** shows:
- Total observations by category (bar chart)
- Severity distribution (pie chart)
- Average RPN by category (bar chart)
- Observation status breakdown
- Top 10 failures by RPN (table)

**FMA Analytics Page** shows:
- Executive summary with totals
- All above charts in larger detail
- Mitigation status overview
- Category deep dive with progress bars
- Key insights & recommendations

---

## 🔗 API Endpoints

### Dashboard
- `GET /` - Main dashboard
- `GET /fma` - FMA analytics page

### Sites
- `GET /sites` - List all sites
- `POST /sites/create` - Create new site

### Process Paths
- `GET /paths` - List paths
- `GET /paths/{id}` - View path details
- `POST /paths/create` - Create new path
- `POST /paths/{id}/steps` - Add step to path

### Observations
- `GET /observations/{id}` - View observation detail
- `POST /observations/create` - Log new waste observation
- `POST /observations/{id}/status` - Update status
- `POST /observations/{id}/comments` - Add comment

### FMA (New!)
- `GET /api/fma-data` - Get FMA analytics data (JSON)
- `POST /fma/{obs_id}/update` - Update FMA analysis
- `POST /fma/{obs_id}/mitigation` - Update mitigation status

---

## 🆘 Troubleshooting

### Server won't start
```bash
# Check if port 8001 is in use
netstat -ano | findstr :8001

# Kill the process if needed (on Windows)
taskkill /PID <process_id> /F

# Try a different port
uvicorn app.main:app --reload --port 8002
```

### Database issues
```bash
# Reset database (deletes all data!)
del timwood.db

# Server will recreate on next start
python run.py
```

### Port conflict with Teams
- Teams uses port 8080
- This app uses port 8001 (default) or 8002
- If still conflicting, use: `uvicorn app.main:app --reload --port 9000`

---

## 📝 Contributing

This dashboard is built for Walmart NS operations. To contribute:

1. Test thoroughly with real operational data
2. Maintain WCAG 2.2 Level AA compliance
3. Follow Lean manufacturing principles
4. Document changes in this guide

---

## 🔐 Data Privacy

- All data is stored locally in SQLite (`timwood.db`)
- No cloud transmission
- Suitable for site-level analysis
- For multi-site rollout, consider database migration strategy

---

## 📞 Support

**Questions or issues?**
- Code Puppy: https://puppy.walmart.com
- Teams: [Code Puppy Teams Channel](https://teams.microsoft.com/l/channel/19%3AGbP8DGJjrXq1sL3IlXErZc5U7hk-IEqsokmnImcKyP41%40thread.tacv2/General)
- Slack: [#code-puppy](https://walmart.enterprise.slack.com/archives/C094Y1D24JY)

---

## 📄 License

Built with ❤️ for Walmart NS Fulfillment Centers

**Last Updated**: April 2026
