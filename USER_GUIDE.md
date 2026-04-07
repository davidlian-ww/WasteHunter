# TIMWOOD Dashboard - Complete User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Managing Sites](#managing-sites)
4. [Creating Process Paths](#creating-process-paths)
5. [Building Process Flows](#building-process-flows)
6. [Tracking Waste](#tracking-waste)
7. [Collaboration & Comments](#collaboration--comments)
8. [Best Practices](#best-practices)

---

## Getting Started

### First Time Setup
1. Navigate to the `timwood-dashboard` folder
2. Double-click `start.bat` (Windows)
3. The app will automatically:
   - Activate the virtual environment
   - Create sample data (first run only)
   - Open your browser to http://localhost:8000

### Manual Start
```bash
# Activate environment
.venv\Scripts\activate

# Run the server
python run.py
```

---

## Dashboard Overview

When you open the app, you'll see:

### Stats Cards (Top)
- **Total Sites**: Number of FCs/DCs configured
- **Process Paths**: Total process flows created
- **Observations**: Total waste observations logged
- **Open Issues**: Unresolved waste observations

### TIMWOOD Categories Reference
Interactive cards showing all 7 waste types with descriptions:
- 🚛 Transportation
- 📦 Inventory
- 🚶 Motion
- ⏱️ Waiting
- 📊 Overproduction
- ⚙️ Over-processing
- ❌ Defects

### Recent Observations
Table showing the latest waste observations with filters for:
- Waste category
- Status (Open, In Progress, Resolved, Closed)

---

## Managing Sites

### View Sites
Click **Sites** in the navigation bar to see all configured locations.

### Add a New Site
1. Click **"+ Add New Site"**
2. Fill in the form:
   - **Site Name**: Full name (e.g., "Portland Fulfillment Center")
   - **Site Code**: Short code (e.g., "PDX1")
   - **Location**: City/State (optional)
   - **Type**: FC, DC, SC, or Other
3. Click **"Create Site"**

### Site Card Features
Each site card shows:
- Site icon and type badge
- Full name and code
- Location
- Creation date
- **"View Process Paths"** button to see that site's processes

---

## Creating Process Paths

### What is a Process Path?
A process path represents a complete workflow or operational process within a site (e.g., "Inbound Receiving", "Order Picking", "Returns Processing").

### Create a Process Path
1. Click **"Process Paths"** in navigation
2. Click **"+ Create Process Path"**
3. Fill in the form:
   - **Site**: Select which FC/DC
   - **Process Path Name**: Descriptive name
   - **Description**: What this process covers (optional)
   - **Created By**: Your name
4. Click **"Create Path"**

You'll be automatically taken to the path detail page to start building.

---

## Building Process Flows

### Add Process Steps
Process steps are the individual stages in your workflow.

1. On the path detail page, use the **yellow "Add Process Step"** section
2. Enter:
   - **Step Name**: e.g., "Unload Truck", "Quality Check"
   - **Description**: Optional details
3. Click **"Add Step"**

Steps will appear in order (1, 2, 3...) showing the flow sequence.

### Step Features
Each step shows:
- Step number (in blue circle)
- Step name and description
- **"+ Report Waste"** button
- List of all waste observations for that step

---

## Tracking Waste

### Report a Waste Observation
1. Navigate to a process path
2. Find the relevant step
3. Click **"+ Report Waste"**
4. Fill in the modal:
   - **Waste Category**: Select from TIMWOOD (required)
   - **Title**: Brief summary (required)
   - **Detailed Description**: Full explanation
   - **Severity**: Low, Medium, High, or Critical
   - **Observed By**: Your name
5. Click **"Report Waste"**

### Waste Categories Explained

**Transportation** 🚛
- Example: Truck parking far from dock
- Example: Multiple handoffs between zones

**Inventory** 📦
- Example: Staged pallets blocking aisles
- Example: Overstocked slow-moving items

**Motion** 🚶
- Example: Excessive walking to equipment
- Example: Poor workstation layout

**Waiting** ⏱️
- Example: Waiting for quality inspector
- Example: System downtime

**Overproduction** 📊
- Example: Processing items before orders
- Example: Creating excess work-in-progress

**Over-processing** ⚙️
- Example: Redundant scanning steps
- Example: Unnecessary paperwork

**Defects** ❌
- Example: Picking errors
- Example: Damaged goods

### Severity Levels

- **Low**: Minor impact, easy fix
- **Medium**: Moderate impact, manageable
- **High**: Significant impact, needs attention
- **Critical**: Severe impact, immediate action required

---

## Collaboration & Comments

### View Observation Details
1. Click **"View Details"** on any observation
2. You'll see:
   - Full observation details
   - Site/Path/Step context
   - Current status
   - All comments/discussion

### Update Status
1. On the observation detail page
2. Use the **"Update Status"** dropdown
3. Select new status:
   - **Open**: Just reported, not yet addressed
   - **In Progress**: Being worked on
   - **Resolved**: Solution implemented
   - **Closed**: Verified complete
4. Click **"Update Status"**

### Add Comments
1. Scroll to the **Discussion** section
2. Enter your name
3. Type your comment/update
4. Click **"Post Comment"**

Use comments to:
- Propose solutions
- Report progress
- Ask questions
- Document what was tried
- Confirm resolution

---

## Best Practices

### Organizing Your Study

1. **Start with Core Processes**
   - Focus on high-volume operations first
   - Create paths for main workflows (Inbound, Picking, Packing, Shipping)

2. **Be Specific with Steps**
   - Break processes into discrete, observable steps
   - Use action verbs (Unload, Scan, Sort, Pack)

3. **Consistent Naming**
   - Use standard naming conventions across sites
   - Example: "IB-01: Unload", "IB-02: Quality Check"

### Effective Waste Reporting

1. **Be Descriptive**
   - Provide enough detail for others to understand
   - Include frequency/impact information

2. **Use Correct Categories**
   - Match waste to the right TIMWOOD type
   - When in doubt, add clarification in description

3. **Set Appropriate Severity**
   - Critical: Impacts safety or major financial loss
   - High: Significant inefficiency or customer impact
   - Medium: Noticeable but manageable
   - Low: Minor optimization opportunity

### Collaboration Tips

1. **Regular Reviews**
   - Schedule weekly reviews of new observations
   - Update statuses as work progresses

2. **Action-Oriented Comments**
   - Propose specific solutions
   - Assign ownership in comments
   - Set target dates

3. **Close the Loop**
   - Verify solutions before closing
   - Document what worked in final comment

### Sample Workflow

**Week 1-2**: Setup
- Create all sites
- Build process paths for main operations
- Train team on TIMWOOD concepts

**Week 3-4**: Observation Phase
- Associates report waste as they see it
- Aim for at least 3-5 observations per process
- Focus on high-impact areas

**Week 5-6**: Analysis & Action
- Review all observations with team
- Prioritize by severity and impact
- Assign owners to top issues

**Week 7-8**: Implementation
- Implement solutions
- Update statuses to "In Progress"
- Monitor effectiveness

**Week 9+**: Continuous Improvement
- Close resolved items
- Report new waste as it emerges
- Share wins across sites

---

## Keyboard Shortcuts & Tips

- Use browser **Ctrl+F** to search observations
- Filter by category on dashboard for focus areas
- Bookmark frequently used paths
- Export data (feature coming soon!)

---

## Troubleshooting

**App won't start?**
- Make sure port 8000 is not in use
- Check that virtual environment is activated
- Try `python run.py` manually

**Can't see my changes?**
- Try refreshing the page (F5)
- Check that you're on the right site/path

**Database reset?**
- Delete `timwood.db` file
- Run `python seed_data.py` to recreate sample data

---

## Support & Feedback

Built with ❤️ by Code Puppy for Walmart NS Operations

Questions or ideas? Connect with the Code Puppy community:
- **Teams**: [Code Puppy Channel](https://teams.microsoft.com/l/channel/19%3AGbP8DGJjrXq1sL3IlXErZc5U7hk-IEqsokmnImcKyP41%40thread.tacv2/General)
- **Slack**: [#code-puppy](https://walmart.enterprise.slack.com/archives/C094Y1D24JY)
- **Workshop**: https://puppy.walmart.com/doghouse

---

**Happy Waste Hunting! 🗑️🎯**
