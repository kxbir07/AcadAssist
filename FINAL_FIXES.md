# AcadAssist Final Assessment Fixes

This build fixes the Assessment page issues found during manual testing.

## Fixed

1. **Question count selector**
   - 5, 10, 15, and 20 now send the actual selected numeric value to the backend.
   - Backend quiz requests are capped at 20 questions.

2. **Document-authoritative assessment generation**
   - When `document_id` is supplied, the selected document's stored `subject_id` and `course_id` are authoritative.
   - A mismatched Subject/Course dropdown cannot filter out the selected document.

3. **Document retrieval resilience**
   - Azure AI Search remains the primary retrieval path.
   - If a document's Azure index is partial/stale, processed database chunks for that exact document can supplement retrieval.
   - Retrieval remains restricted to the selected document and authenticated user.

4. **Grounded quiz generation**
   - Document-based quizzes do not use the static/demo question bank.
   - Microsoft Foundry is asked for exactly the requested number of questions.
   - If Foundry returns fewer, additional grounded generation attempts are made and duplicate questions are removed.
   - Questions are grounded only in retrieved document chunks.

5. **Document metadata consistency**
   - Quiz entities and generated questions use the selected document's authoritative subject/course metadata.

## Run

### Backend

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

Copy `.env.example` to `.env` and enter your Azure configuration. Never share `.env` or commit secrets.

## Recommended manual tests

- Ethernet (1).pdf -> 5 questions
- Ethernet (1).pdf -> 10 questions
- Reference Models.pdf -> 5 questions
- Computer Networks Protocols -> 5 questions
- Select a document and intentionally choose a different Subject -> document should remain authoritative
- Request 20 questions -> UI sends 20 and backend accepts it
