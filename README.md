# AcadAssist

**AI-Powered Personalized Academic Study Assistant**

AcadAssist is an intelligent, multi-modal academic companion built to help university students organize course materials, generate grounded summaries, take adaptive practice quizzes, track exam deadlines, and plan daily study sessions with zero-trust security.

---

## Architecture Overview

```text
React / TypeScript / Vite Frontend
            |
            | Authenticated HTTP / JWT Bearer Requests (No client user_id)
            v
      FastAPI Backend
            |
            | Server-derived current_user identity
            v
    Unified AcadAssist Services
       /       |        \
      /        |         \
Knowledge   Assessment   Study Intelligence
  (RAG)     (Quizzes)    (Planner / Analytics)
     |         |          |
     v         v          v
PostgreSQL / Local SQLite Database
     |
     +--------------------------+
     |                          |
     v                          v
Local Storage            Azure Blob Storage (Entra ID)
     |                          |
     +------------+-------------+
                  |
                  v
          Azure AI Search (Hybrid BM25 + Vector)
                  |
                  v
         Azure OpenAI / Microsoft Foundry
                  |
                  v
         AcadAssist Agent Orchestrator
                  |
                  v
         11 Authorized Academic Tools
```

---

## Subsystems & Team Architecture

* **Person 1 — Azure Infrastructure & Microsoft Foundry:**
  * Cloud infrastructure integration with Entra ID (`DefaultAzureCredential`).
  * Azure Blob Storage with private container isolation and short-lived SAS access.
  * Azure AI Search with 19-field metadata schema and mandatory server-side security filter: `(user_id eq '{user_id}' or visibility eq 'public')`.
  * Centralized `AcadAssistAgentService` orchestrator with grounded tool loop and execution modes (`cloud_foundry` when configured, `local_orchestrator` fallback for local dev).
  * 11 authorized academic tools registered in `foundry_openapi.json`.
* **Person 2 — Knowledge Base & Document Processing:**
  * Multi-format document ingestion pipeline (PDF, PPTX, DOCX, TXT).
  * Document text extraction, cleaning, chunking, and embedding generation.
  * Document ownership and visibility access control (`verify_document_access`).
* **Person 3 — Assessment & Practice Quizzes:**
  * Adaptive question generation grounded in course materials.
  * Quiz submission, automated grading, performance analytics, and non-repeating questions.
* **Person 4 — Study Intelligence & Planner:**
  * Weak topic identification and study recommendations.
  * Upcoming exam tracking and daily study schedule optimization.
  * Course progress tracking and weekly study performance reports.
* **Person 5 — Modern React UI:**
  * Built with React, TypeScript, and Vite.
  * Responsive navigation, light/dark theme support, and unified subsystem views:
    * **Dashboard:** Real-time stats, upcoming deadlines, study recommendations.
    * **Assistant:** Context-aware chat with tool citations and action items.
    * **Knowledge:** Document repository, upload wizard, summary viewer.
    * **Assessment:** Adaptive practice quizzes and score history.
    * **Planner:** Calendar, focus timer, and AI study strategy.
    * **Progress:** Mastery radar, weekly hours, and activity logs.

---

## Security & Zero Trust Model

1. **Server-Derived Identity:**  
   Every sensitive endpoint (`POST /api/chat`, `/api/tools/*`, `/api/documents/*`) enforces `current_user: User = Depends(get_current_user)`. The client cannot choose the identity under which a request runs.
2. **Client `user_id` Rule:**  
   The React frontend never transmits `user_id`. If a client sends a conflicting `user_id`, the backend immediately rejects it with `HTTP 403 Forbidden`.
3. **LLM `user_id` Anti-Impersonation:**  
   The tool dispatcher strictly overrides any model-generated `user_id` argument with the authenticated server-side `user_id`.
4. **Document & Search Isolation:**  
   Documents and search chunks strictly enforce owner or public visibility: `(user_id eq '{user_id}' or visibility eq 'public')`. Private documents remain completely inaccessible to other users.
5. **Visibility Synchronization:**  
   Updating a document's visibility (`private <-> public`) synchronizes both the database and the search index, with explicit compensation handling to preserve consistency.

---

## Getting Started

### Prerequisites

* Python 3.11+
* Node.js 18+ and npm

### 1. Backend Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your local settings (or use safe dev defaults)

# Run tests
pytest -q

# Start FastAPI backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend API will be available at `http://localhost:8000` with Swagger docs at `http://localhost:8000/docs`.

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run lint checks
npm run lint

# Build production bundle
npm run build

# Start Vite dev server
npm run dev
```

The React frontend will be accessible at `http://localhost:5173`.

---

## Execution Modes

| Component | Local / Offline Development | Production Cloud (`ENVIRONMENT=production`) |
| :--- | :--- | :--- |
| **Database** | SQLite (`data/acadassist.db`) | PostgreSQL |
| **Document Storage** | `LocalStorageService` (`storage/`) | `AzureBlobStorage` (`AZURE_STORAGE_CONTAINER`) |
| **Search Engine** | `LocalHybridSearchIndex` (BM25 + Cosine) | `AzureSearchService` (`AZURE_SEARCH_ENDPOINT`) |
| **Embeddings** | `LocalDeterministicEmbeddingProvider` | Azure OpenAI (`text-embedding-3-small`) |
| **Agent Execution** | `local_orchestrator` | `cloud_foundry` (`FOUNDRY_PROJECT_ENDPOINT`) |

---

## Verification & Testing

```bash
# Run full backend test suite
pytest -v

# Run Person 1 security isolation suite
pytest -v tests/test_person1_security.py

# Verify frontend
cd frontend
npm run lint
npm run build
```
