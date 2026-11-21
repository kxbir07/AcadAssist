# AcadAssist — Bugs Identified & Fixed

## 1. Backend Bugs Fixed

### Bug 1: Failing User Isolation Test (`tests/test_auth_and_isolation.py::test_quiz_attempts_and_upcoming_exams_user_isolation`)
- **Root Cause**: The test scheduled an exam with a hardcoded date `"2026-10-15T09:00:00"`, which is in the past relative to current UTC time (`2026-11-15`), causing `GET /api/exams/upcoming` to filter the exam out and fail `assert len(exams_a) == 1`. Additionally, the test only checked upcoming exams and did not verify cross-user quiz access (`403`), cross-user quiz submission (`403`), or `/api/quizzes/attempts` user isolation.
- **Fix**: Updated `tests/test_auth_and_isolation.py` to use `(datetime.now(timezone.utc) + timedelta(days=10)).isoformat()` and added complete assertions verifying that User A's quiz cannot be viewed or submitted by User B (`403 Forbidden`) and does not leak into User B's `/api/quizzes/attempts` or `/api/exams/upcoming`.

### Bug 2: Failing Foundry Configuration Test (`tests/test_foundry.py::test_foundry_manager_missing_endpoint_error`)
- **Root Cause**: `FoundryProjectManager.is_configured` checked `settings.FOUNDRY_PROJECT_ENDPOINT`, `settings.AZURE_OPENAI_ENDPOINT`, and `settings.AZURE_OPENAI_API_KEY` from the global `settings` singleton loaded from `.env` even when `monkeypatch.delenv` cleared environment variables during the test.
- **Fix**: Updated the autouse `test_environment` fixture in `tests/conftest.py` to clear cloud endpoint/key attributes on `settings` during unit tests (`ENVIRONMENT="test"`), ensuring deterministic unit test isolation without modifying `.env`.

### Bug 3: Repeated Azure Credential Network Timeouts During Local/Offline Execution
- **Root Cause**: `AzureStorageService`, `AzureSearchService`, `EmbeddingService`, and `AcadAssistAgentService` attempted live Azure network calls or `DefaultAzureCredential` token acquisition on every request when cloud services were unreachable, causing multi-second delays per request.
- **Fix**: Added fast `ENVIRONMENT == "test"` bypasses and `_cloud_unreachable` connection-failure caching in `app/services/storage/azure_storage.py`, `app/services/rag/search.py`, `app/services/rag/embedding.py`, and `app/azure/agent.py`, plus quote stripping in `app/config.py`.

### Bug 4: Singleton State Isolation Across `AzureSearchService` Instances
- **Root Cause**: `app/services/rag/pipeline.py` indexed document chunks into `get_search_service()`, whereas `app/azure/adapters.py` (`KnowledgeRetrievalAdapter` and `QuizGenerationAdapter`) instantiated separate `AzureSearchService()` objects with empty in-memory fallback dictionaries.
- **Fix**: Updated `app/azure/adapters.py` to use the shared `get_search_service()` and `get_embedding_service()` singletons and passed `document_id` in `ToolDispatcher.dispatch("search_knowledge")`.

### Bug 5: Offline Document-Grounded Quiz Generation Returning `insufficient_material`
- **Root Cause**: When generating a quiz for a specific uploaded `document_id` while Azure Foundry was offline, `QuizGenerationAdapter.generate_quiz` logged a warning and left `all_questions` empty, returning `status: "insufficient_material"` even when valid document chunks existed.
- **Fix**: Implemented deterministic chunk-grounded MCQ synthesis in `app/azure/adapters.py` that builds 4-option multiple-choice questions with page/section citations directly from the uploaded document's extracted chunks whenever cloud LLM generation is unavailable in local development/test modes.

### Bug 6: Missing Password Management, Recovery & Workspace Persistence Endpoints
- **Root Cause**: `app/api/routes/auth.py` only implemented `/register`, `/login`, `/me`, and `/logout`.
- **Fix**: Added `PATCH/PUT /api/auth/profile`, `POST /api/auth/change-password`, `POST /api/auth/forgot-password`, `POST /api/auth/reset-password` (using single-use password-hash-fingerprinted JWT reset tokens), and `GET/PUT /api/auth/workspace-state`, and idempotently migrated `workspace_state` onto `users` in `app/models/shared.py` and `app/database/session.py`.

### Bug 7: Study Planner Empty Tasks for Newly Registered Users
- **Root Cause**: `create_study_plan` in `app/services/planner.py` only scheduled topics present in the `topics` SQL table and `topic_mastery` table, ignoring topics from `QuestionAttempt` records or `upcoming_exams` when `topics` was unseeded.
- **Fix**: Updated `app/services/person3_client.py` to synthesize `TopicMastery` from `QuestionAttempt` + `Question` rows and updated `app/services/planner.py` to include user mastery topics and upcoming exam preparation topics when generating study tasks.

---

## 2. Frontend Bugs Fixed

### Bug 8: TypeScript Build Failure in `CourseDetail.tsx` (`TS6133`)
- **Root Cause**: `src/pages/CourseDetail.tsx(30,8): error TS6133: 'lessonIds' is declared but its value is never read.` prevented `npm run build` (`tsc -b && vite build`) from succeeding.
- **Fix**: Removed the unused `lessonIds` variable in `frontend/src/pages/CourseDetail.tsx`. Verified `./node_modules/.bin/tsc -b` completes with **0 errors**.

### Bug 9: Disconnected Frontend Authentication (`frontend/src/services/auth.ts`)
- **Root Cause**: `frontend/src/services/auth.ts` stored accounts in browser `localStorage` (`acadassist.auth.accounts.v1`) with plaintext passwords and never called `/api/auth/*`.
- **Fix**: Rewrote `frontend/src/services/auth.ts`, `frontend/src/context/AuthContext.tsx`, and `frontend/src/pages/Login.tsx` to authenticate against `/api/auth/login`, `/api/auth/register`, `/api/auth/me`, `/api/auth/profile`, `/api/auth/change-password`, `/api/auth/forgot-password`, `/api/auth/reset-password`, and `/api/auth/logout`.

### Bug 10: Duplicate Chat Messages Persisted on Every AI Assistant Turn
- **Root Cause**: `POST /api/chat` already saves both the user prompt and assistant response in SQLite, but `Assistant.tsx` also called `appendChatMessage` twice after `sendChatMessage`, creating duplicate rows in `chat_messages`.
- **Fix**: Removed the redundant `appendChatMessage` calls in `frontend/src/pages/Assistant.tsx` and added source citation cards and execution mode badges.

### Bug 11: Shared Browser Storage Across Different User Accounts
- **Root Cause**: `AppContext.tsx` used static keys (`acadassist.enrolledCourses.v2`, `acadassist.courseProgress.v2`, etc.) without scoping by `user.id`, causing one user's enrolled courses and lesson completions to bleed into another user's view on the same browser.
- **Fix**: Scoped all workspace storage keys per authenticated user ID (`acadassist.workspace.<userId>.*`) and synchronized them with `GET/PUT /api/auth/workspace-state`.
