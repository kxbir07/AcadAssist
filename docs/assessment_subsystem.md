# AcadAssist — Assessment Subsystem Documentation (Person 3)

## 1. Overview & Responsibilities

The Assessment Subsystem (Person 3) provides the core testing, evaluation, question bank management, and academic mastery engine for the AcadAssist platform. It deterministically assesses student knowledge, tracks per-student attempt history, drives adaptive question difficulty, detects weak and strong academic topics, and provides exam-proximity-driven study recommendations.

### Key Responsibilities:
- **Quiz & Question Storage**: Full relational schema supporting UUID primary and foreign keys in the shared application database.
- **Granular Attempt Tracking**: Stores high-level `QuizAttempt` and uniquely identifiable `QuestionAttempt` rows.
- **Deterministic Scoring**: 100% backend-authoritative evaluation (zero LLM dependency for correctness or score calculation).
- **Per-Student No-Repeat Logic**: Excludes previously attempted questions based on recorded attempt history.
- **Adaptive Difficulty**: Computes recommended difficulty (`easy`, `medium`, `hard`) using centralized, configurable performance thresholds.
- **Performance Analytics & Topic Mastery**: Computes overall accuracy, topic accuracy, difficulty accuracy, recent accuracy, and topic mastery ratios.
- **Weak & Strong Topic Detection**: Classifies topics based on configurable mastery thresholds for consumption by Study Intelligence (Person 4).
- **Exam-Aware Assessment**: Schedules exams and computes assessment focus based on remaining days until the exam.
- **Modular Integration Boundaries**: Exposes clean Python interfaces for Foundry Agent tools (Person 1) and accepts `source_chunk_id` for RAG integration (Person 2).

---

## 2. Database Entities & Schemas

The Assessment subsystem lives in the **shared application database** (SQLAlchemy 2.0 ORM with SQLite default or PostgreSQL via `DATABASE_URL`).

```
┌─────────────────────────────────────────────────────────────┐
│                            Quiz                             │
├─────────────────────────────────────────────────────────────┤
│ quiz_id (PK, UUID)                                          │
│ user_id (indexed)                                           │
│ course_id                                                   │
│ subject_id (indexed)                                        │
│ title                                                       │
│ difficulty ('easy' | 'medium' | 'hard')                     │
│ question_count (int)                                        │
│ created_at (datetime)                                       │
└──────────────┬───────────────────────────────┬──────────────┘
               │ 1..N                          │ 1..N
               ▼                               ▼
┌──────────────────────────────┐ ┌────────────────────────────┐
│           Question           │ │        QuizAttempt         │
├──────────────────────────────┤ ├────────────────────────────┤
│ question_id (PK, UUID)       │ │ attempt_id (PK, UUID)      │
│ quiz_id (FK -> quizzes)      │ │ quiz_id (FK -> quizzes)    │
│ subject_id (indexed)         │ │ user_id (indexed)          │
│ topic_id (indexed)           │ │ started_at (datetime)      │
│ question_text (text)         │ │ completed_at (datetime)    │
│ question_type ('mcq')        │ │ score (int, correct count) │
│ difficulty                   │ └─────────────┬──────────────┘
│ options (JSON list)          │               │ 1..N
│ correct_answer (text)        │               │
│ explanation (text)           │               │
│ source_chunk_id (indexed)    │               │
└──────────────┬───────────────┘               │
               │ 1..N                          │
               └───────────────┐ ┌─────────────┘
                               ▼ ▼
               ┌─────────────────────────────────┐
               │         QuestionAttempt         │
               ├─────────────────────────────────┤
               │ question_attempt_id (PK, UUID)  │
               │ attempt_id (FK -> quiz_attempts)│
               │ question_id (FK -> questions)   │
               │ user_id (indexed)               │
               │ selected_answer (text)          │
               │ is_correct (bool)               │
               │ time_taken (float seconds)      │
               │ attempted_at (datetime)         │
               │ UQ: (attempt_id, question_id)   │
               └─────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                            Exam                             │
├─────────────────────────────────────────────────────────────┤
│ exam_id (PK, UUID)                                          │
│ user_id (indexed)                                           │
│ course_id                                                   │
│ subject_id (indexed)                                        │
│ title                                                       │
│ exam_date (datetime)                                        │
│ created_at (datetime)                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Core Assessment Lifecycles

### A. Quiz Creation & Generation Lifecycle
1. Client/Agent calls `POST /api/quizzes` with `subject_id`, optional `topic_ids`, `difficulty`, `count`.
2. `AdaptiveDifficultyService` resolves difficulty (if not explicitly specified) from historical user accuracy.
3. `QuestionGenerator` generates candidate questions for the subject, topic, and difficulty.
4. `NoRepeatService` inspects the user's `QuestionAttempt` history and discards any previously attempted questions.
5. The `Quiz` and `Question` records are saved and committed to the database.
6. The public `QuizResponse` is returned with `correct_answer` masked.

### B. Quiz Submission & Deterministic Scoring Lifecycle
1. Client/React submits student answers to `POST /api/quizzes/{quiz_id}/submit`.
2. `ScoringService` validates that the quiz exists and belongs to the authenticated `user_id`.
3. Validates that the quiz has not already been submitted (rejects duplicate attempts with `409 Conflict`).
4. Compares each `selected_answer` against the stored `correct_answer` using deterministic string matching.
5. Computes `score` (count of correct answers) and `percentage`.
6. Creates granular `QuestionAttempt` records and `QuizAttempt`.
7. Computes topic accuracy, weak topics (`mastery < 0.60`), and strong topics (`mastery >= 0.75`).
8. Returns authoritative `QuizSubmissionResponse`.

---

## 4. Business Rules & Configurable Thresholds

All business logic rules are centralized in [`app/core/config.py`](file:///app/core/config.py):

| Rule / Concept | Default Threshold | Description |
| :--- | :--- | :--- |
| **Adaptive Easy** | `< 50.0%` | Adapts quiz difficulty to `easy` (revision focus). |
| **Adaptive Medium** | `50.0% – 75.0%` | Adapts quiz difficulty to `medium`. |
| **Adaptive Hard** | `> 75.0%` | Adapts quiz difficulty to `hard`. |
| **Weak Topic** | `< 0.60` mastery | Classified as a weak topic requiring remediation. |
| **Strong Topic** | `>= 0.75` mastery | Classified as a strong topic. |
| **Exam Proximity >14d** | `> 14 days` | `normal` assessment focus. |
| **Exam Proximity 7–14d** | `7 – 14 days` | `increased` assessment focus. |
| **Exam Proximity 3–7d** | `3 – 7 days` | `targeted_weak_topic` assessment focus. |
| **Exam Proximity <=2d** | `<= 2 days` | `revision_and_targeted` assessment focus. |

---

## 5. Agent & Subsystem Integration Boundaries

### A. Foundry Agent Integration (Person 1)
The Foundry Agent can directly invoke functions exposed by `app.assessment.services.quiz_service.quiz_service`:
- `generate_quiz(user_id, subject_id, topic_ids, difficulty, count)`
- `submit_quiz(user_id, quiz_id, answers)`
- `get_performance(user_id, subject_id)`
- `get_weak_topics(user_id, subject_id)`
- `get_upcoming_exams(user_id, subject_id)`

### B. Knowledge Base & RAG Integration (Person 2 & 4)
- `Question.source_chunk_id`: Stores the source chunk UUID provided during question generation.
- No direct search or document chunking is implemented in Assessment; Assessment receives source metadata through the clean question interface.

### C. Study Planner & Intelligence Integration (Person 4)
- Person 4 consumes `get_weak_topics(user_id)` and `get_upcoming_exams(user_id)` to formulate personalized study roadmaps.

---

## 6. API Endpoints Reference

| Method | Endpoint | Summary |
| :--- | :--- | :--- |
| `POST` | `/api/quizzes` | Generate adaptive, non-repeating quiz |
| `GET` | `/api/quizzes/{quiz_id}` | Retrieve quiz questions (user-isolated) |
| `POST` | `/api/quizzes/{quiz_id}/submit` | Authoritative deterministic quiz evaluation |
| `GET` | `/api/performance` | Retrieve student performance metrics |
| `GET` | `/api/performance/weak-topics` | Retrieve detected weak topics list |
| `POST` | `/api/exams` | Schedule an academic exam |
| `GET` | `/api/exams` | List student exams |
| `GET` | `/api/exams/upcoming` | List upcoming future exams |
| `GET` | `/health` | Application health check |

---

## 7. Testing Strategy

The test suite is located in `tests/` and covers 28+ test cases:
1. `tests/test_quiz_creation.py`: Quiz generation, question generation, and retrieval.
2. `tests/test_scoring_and_submission.py`: Correct/incorrect scoring, duplicate rejection, and error cases.
3. `tests/test_user_isolation.py`: Strict multi-user tenant isolation.
4. `tests/test_no_repeat.py`: Deterministic per-student no-repeat and pool exhaustion handling.
5. `tests/test_adaptive_difficulty.py`: Difficulty transitions (<50%, 50-75%, >75%) and configurable thresholds.
6. `tests/test_performance_and_analytics.py`: Accuracy metrics, mastery ratios, and weak/strong topic detection.
7. `tests/test_exams.py`: Exam creation, upcoming exam retrieval, proximity focus rules.
8. `tests/test_api_endpoints.py`: FastAPI HTTP endpoint tests using TestClient.
9. `tests/test_os_end_to_end.py`: Mandatory 11-step Operating Systems simulation test.
