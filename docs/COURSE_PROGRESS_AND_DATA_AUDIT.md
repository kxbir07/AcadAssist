# AcadAssist — Course Progress & Data Audit

## Dataset
- Courses: **1,810**
- Modules: **31,413**
- Lessons: **31,413**
- Module quizzes: **31,413**
- Final quizzes: **1,810**
- Module quiz size: **12 questions each**
- Final quiz size: **30 questions each**

## Progress architecture
The application now uses one persisted `acadassist.courseProgress` state for course learning/assessment activity. Lesson completion, module quiz completion, final quiz completion, quiz results, last lesson and last activity are stored there.

`frontend/src/utils/courseProgress.ts` contains the shared course/module progress calculations. Course, Courses, Dashboard, Progress and Subjects synchronization consume the same model.

## Lesson content
The dataset stores compact local curriculum blueprints. `LessonPage` expands a compact lesson into a structured long-form local study lesson using the course name, module title and coverage. The rendered structure includes objectives, definitions, headings, bullets, numbered steps, a comparison table, worked scenario, applications/limitations, common mistakes, exam tip, key takeaways and quick revision.

## Quiz data
- Every module has a 12-question module quiz.
- Every course has a 30-question final quiz.
- Final quiz questions were regenerated to avoid exact duplication with module quiz questions.
- Course quiz completion and score remain separate concepts.

## Validation
`node frontend/scripts/validateCourseDataset.mjs` returned **PASS** with no dataset errors.

## Build verification
The packaging environment could not complete `npm install` because the npm registry dependency download timed out. Therefore the TypeScript/Vite build is **not claimed as PASS** here. On Windows run:

```powershell
cd "...\AcadAssist-Course-Quiz-Integrated\frontend"
npm.cmd install
npm.cmd run validate:courses
npm.cmd run build
```
