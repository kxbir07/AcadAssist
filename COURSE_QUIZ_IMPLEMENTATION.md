# AcadAssist Course + Course-Quiz Integration

This build integrates the supplied subject dataset as a local Course system.

## Two quiz systems
- Course-associated quizzes: static local course data under `frontend/public/data/courses/`; answers/results are persisted in browser localStorage.
- User/document quizzes: existing Assessment/Knowledge/Azure workflow was not modified by this implementation.

## Local storage keys
- `acadassist.enrolledCourses`
- `acadassist.courseProgress`
- `acadassist.courseQuizResults`

## Routes
- `/courses`
- `/courses/:courseId`
- `/courses/:courseId/quiz`

## Dataset
The generated local catalog contains 1,810 subject courses, an index file, module/lesson data, and course-associated quiz data. Course data is loaded from local static assets and does not require Azure.

## Verification performed
- TypeScript project build check (`tsc -b`): PASS.
- Dataset integrity: 1,810 index entries, 1,810 course files, 1,810 unique IDs, no missing course files, no invalid quiz question answer indexes.
- Full Vite bundle could not be completed in the execution environment because the copied dependency tree is missing its platform-specific optional Rolldown native binding. This is a dependency/environment issue rather than a TypeScript error. Run `npm.cmd install` on Windows before `npm.cmd run build`.
