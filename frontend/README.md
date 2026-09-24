# AcadAssist Frontend

Production-style React + TypeScript + Vite frontend for AcadAssist.

## Run

```powershell
npm.cmd install
npm.cmd run dev
```

Production build:

```powershell
npm.cmd run build
```

## Architecture

- React + TypeScript + Vite
- Local-first state in `src/context/AppContext.tsx`
- Browser persistence with `localStorage`
- Uploaded file blobs persisted with IndexedDB in `src/services/fileStore.ts`
- Azure/backend boundary in `src/services/api.ts`
- UI components do not call Azure directly

When Azure APIs are ready, set `VITE_API_URL` and replace the service implementations without rewriting page components.

## Main flows

- Dashboard: progress, focus tasks, upcoming events, calendar, recommendations
- Courses: search/filter, course details, add/remove from My Subjects
- Knowledge: upload, subject filtering, document preview/download, edit, star, delete, AI note drafts
- Assessment: topic/document/note quiz generation, timed exam mode, scoring, retry/history
- Planner: day/week/month views, CRUD events, completion, focus timer
- AI Assistant: local study responses, prompt tools, voice input where supported, persistent chat
- Progress: live metrics based on subjects, quizzes and planner events
- Settings/Profile: persistent preferences, subject CRUD, profile editing, data export
