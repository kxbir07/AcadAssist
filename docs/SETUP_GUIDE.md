# AcadAssist — Local Development & Setup Guide

## 1. Prerequisites
- **Python**: 3.11 or 3.12+
- **Node.js**: 18.x or 20.x+ (with `npm`)
- **Operating System**: Windows 10/11, macOS, or Linux

---

## 2. One-Command Quick Start
From the project root (`AcadAssist/`), you can start both the FastAPI backend (`http://127.0.0.1:8000`) and the Vite React frontend (`http://localhost:5173`) with a single command:

### Cross-Platform (Python)
```bash
python start_dev.py
```

### Windows Command Prompt
```cmd
start_dev.bat
```

### Windows PowerShell
```powershell
.\start_dev.ps1
```

---

## 3. Step-by-Step Manual Setup

### Step 1 — Backend Environment Setup
```bash
# 1. Create and activate a virtual environment
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Launch the FastAPI backend on port 8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Backend API Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger API Docs**: `http://127.0.0.1:8000/docs`
- **Health Endpoint**: `http://127.0.0.1:8000/health`

### Step 2 — Frontend Environment Setup
Open a second terminal in `frontend/`:
```bash
cd frontend

# Install Node packages (first time or if switching OS platforms)
npm install

# Start Vite development server on port 5173
npm run dev
```
- **Frontend Application URL**: `http://localhost:5173`
- Vite automatically proxies `/api/*` and `/health` requests to `http://127.0.0.1:8000` (configured in `frontend/vite.config.ts`).

---

## 4. Running Tests & Validation

### Run Backend Test Suite
```bash
pytest -q
```

### Run Frontend TypeScript Check & Production Build
```bash
cd frontend
npm run build
```

### Validate the 1,810-Course Curriculum Dataset
```bash
cd frontend
node scripts/validateCourseDataset.mjs
```

---

## 5. Authentication & Password Recovery in Local Development
- **Register / Sign In**: Create a new student account on `/login` or sign in with an existing account.
- **Persistent Session**: Your JWT access token (`acadassist.auth.token`) and per-user workspace state (`GET/PUT /api/auth/workspace-state`) persist across browser refreshes and logout/login cycles.
- **Local Password Recovery**: Click **Forgot password?** on `/login` and enter your registered email address. When SMTP email delivery is not configured in local development, the backend securely issues a 15-minute single-use signed JWT reset token and pre-fills it in the recovery dialog so you can immediately set a new password and sign in.
