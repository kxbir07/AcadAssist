# AcadAssist Course System — Complete Course Content + Quiz + Progress + Profile Selection

## Implemented
- Course JSON assets now contain populated module/lesson content derived from the supplied academic deep-dataset packs where a matching subject pack exists.
- All 1,810 catalog courses have local course JSON data.
- 31,413 modules are represented across the catalog.
- Every module has a local module quiz with 12 questions.
- Every course has a local final quiz with 30 questions.
- Course quizzes are separate from the existing document/user quiz flow.
- Course progress combines:
  - 70% lesson completion
  - 30% course quiz completion
- Quiz score does not determine whether a quiz was attempted/completed.
- Course completion requires all lessons and all course quizzes to be completed.
- Course progress and quiz results remain in localStorage.
- Profile now has searchable learning-field preferences.
- Courses uses selected learning fields as its default scope.
- With no selected field, Courses deterministically shows the first 20 catalog courses by stable ID.
- Added module quiz routing: `/courses/:courseId/modules/:moduleId/quiz`.
- Existing final course quiz route remains `/courses/:courseId/quiz`.

## Local storage
- `acadassist.courseProgress`
- `acadassist.courseQuizResults`
- `acadassist.coursePreferences`
- `acadassist.enrolledCourses`

## Quiz separation
Course quizzes:
`Course -> local course JSON -> local quiz attempt/result -> local progress`

Document/user quizzes:
`User document -> existing Assessment/Knowledge/Azure workflow`

The document quiz code path was not intentionally merged with the Course Quiz system.

## Dataset note
The supplied Ultimate/Expanded academic dataset describes many subject packs as curriculum/knowledge blueprints rather than authoritative lecture notes. The implementation uses those supplied packs as the course-content source where matching subject packs exist; it does not claim they replace instructor-provided or authoritative academic materials.

## Verification
- JSON validation: 1,810/1,810 course files parse successfully.
- Final quiz size: 30 questions for every course.
- Module quiz minimum: 12 questions for every module.
- No course module has zero lessons.
- TypeScript source was updated consistently, but a full TypeScript/Vite build could not be completed in this Linux execution environment because the supplied dependency tree is incomplete (the local `node_modules` copy lacks the required `vite/client` and `@types/node` packages). On Windows, run `npm.cmd install` in `frontend`, then `npm.cmd run build`.
