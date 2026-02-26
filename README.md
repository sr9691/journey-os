# JourneyOS

AI agent orchestration system for B2B marketing automation using LangGraph.

## Quick Start (Windows + VSCode)

### Prerequisites

1. **Install Python 3.11+**
   - Download from https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation

2. **Install Git**
   - Download from https://git-scm.com/download/win
   - Use default options

3. **Install VSCode**
   - Download from https://code.visualstudio.com/
   - Install the Python extension

### Setup

```powershell
# Clone the repository (replace with your repo URL after GitHub setup)
git clone https://github.com/YOUR_USERNAME/content-intelligence-system.git
cd content-intelligence-system

# Create virtual environment
python -m venv .venv

# Activate virtual environment (PowerShell)
.\.venv\Scripts\Activate.ps1

# Or for Command Prompt:
# .\.venv\Scripts\activate.bat

# Install dependencies
pip install -e .

# Copy environment template
copy .env.example .env
# Edit .env with your API keys
```

### Run the Test

```powershell
python test_workflow.py
```

Expected output:
```
✓ Graph executed successfully!
```

## Project Structure

```
content-intelligence-system/
├── pyproject.toml      # Dependencies and project config
├── .env.example        # Environment variable template
├── test_workflow.py    # Test script
├── models/
│   └── state.py        # LangGraph state definitions
├── agents/
│   └── matching/
│       ├── intent_summarizer.py  # Extract intent from prospects
│       └── asset_ranker.py       # Rank content for prospects
└── graphs/
    └── email_generation.py       # Main workflow graph
```

## GitHub Setup Guide

### First Time Setup

1. **Create GitHub account** at https://github.com

2. **Create a new repository**
   - Go to https://github.com/new
   - Name: `content-intelligence-system`
   - Keep it Private
   - DON'T initialize with README (we already have files)

3. **Connect local repo to GitHub** (run in project folder):

```powershell
# Initialize git repository
git init

# Add all files
git add .

# Create first commit
git commit -m "Initial commit: LangGraph scaffolding with email generation workflow"

# Add GitHub remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/content-intelligence-system.git

# Push to GitHub
git push -u origin main
```

### Daily Workflow

```powershell
# Check what's changed
git status

# Stage changes
git add .

# Commit with message
git commit -m "Description of what you changed"

# Push to GitHub
git push
```

### VSCode Git Integration

VSCode has built-in Git support:
1. Click the Source Control icon (left sidebar, branch icon)
2. Stage changes by clicking `+` next to files
3. Type commit message in the text box
4. Click ✓ checkmark to commit
5. Click `...` menu → Push to upload

## Next Steps

- [ ] Add WordPress REST API client
- [ ] Connect to real prospect data
- [ ] Implement Claude API calls for intent analysis
- [ ] Add email template builder
- [ ] Deploy to LangGraph Cloud

## Architecture

```
WordPress ──webhook──> LangGraph ──REST API──> WordPress
                          │
                ┌─────────┴─────────┐
                │                   │
           Claude API          Gemini API
        (intent analysis)   (email generation)
```
