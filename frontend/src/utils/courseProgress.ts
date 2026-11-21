export interface CourseProgressLike {
  completedLessonIds?: string[];
  completedQuizIds?: string[];
  lastLessonId?: string;
  lastActivityAt?: string;
  quizResults?: Record<string, { percentage: number }>;
}

export interface CourseLikeForProgress {
  id: string;
  lessonCount?: number;
  moduleCount?: number;
  modules?: Array<{ id: string; lessons?: Array<{ id: string }> }>;
  moduleQuizzes?: Array<{ id: string; moduleId?: string }>;
  finalQuiz?: { id: string };
  quiz?: { id: string };
}

export interface CourseProgressSummary {
  totalLessons: number;
  completedLessons: number;
  learningPct: number;
  totalQuizzes: number;
  completedQuizzes: number;
  assessmentPct: number;
  overallPct: number;
  completed: boolean;
  lessonRemaining: number;
}

export function getCourseTotals(course: CourseLikeForProgress) {
  const totalLessons = course.modules?.length
    ? course.modules.reduce((sum, module) => sum + (module.lessons?.length || 0), 0)
    : Math.max(0, course.lessonCount || 0);
  const totalModuleQuizzes = course.moduleQuizzes?.length
    ? course.moduleQuizzes.length
    : Math.max(0, course.moduleCount || 0);
  const hasFinalQuiz = Boolean(course.finalQuiz || course.quiz);
  return { totalLessons, totalModuleQuizzes, hasFinalQuiz, totalQuizzes: totalModuleQuizzes + (hasFinalQuiz ? 1 : 0) };
}

export function calculateCourseProgress(course: CourseLikeForProgress, progress?: CourseProgressLike): CourseProgressSummary {
  const totals = getCourseTotals(course);
  const completedLessonIds = new Set(progress?.completedLessonIds || []);
  const completedQuizIds = new Set(progress?.completedQuizIds || []);
  const lessonIds = course.modules?.flatMap(module => (module.lessons || []).map(lesson => lesson.id));
  const quizIds = [
    ...(course.moduleQuizzes || []).map(quiz => quiz.id),
    ...(course.finalQuiz?.id ? [course.finalQuiz.id] : course.quiz?.id ? [course.quiz.id] : []),
  ];
  const completedLessons = lessonIds ? lessonIds.filter(id => completedLessonIds.has(id)).length : Math.min(completedLessonIds.size, totals.totalLessons);
  const completedQuizzes = quizIds.length ? quizIds.filter(id => completedQuizIds.has(id)).length : Math.min(completedQuizIds.size, totals.totalQuizzes);
  const learningPct = totals.totalLessons ? Math.round((completedLessons / totals.totalLessons) * 100) : 0;
  const assessmentPct = totals.totalQuizzes ? Math.round((completedQuizzes / totals.totalQuizzes) * 100) : 0;
  const overallPct = Math.round(learningPct * 0.7 + assessmentPct * 0.3);
  return {
    totalLessons: totals.totalLessons, completedLessons, learningPct,
    totalQuizzes: totals.totalQuizzes, completedQuizzes, assessmentPct, overallPct,
    completed: totals.totalLessons > 0 && completedLessons === totals.totalLessons && totals.totalQuizzes > 0 && completedQuizzes === totals.totalQuizzes,
    lessonRemaining: Math.max(0, totals.totalLessons - completedLessons),
  };
}

export function calculateModuleProgress(module: { id: string; lessons?: Array<{ id: string }> }, moduleQuizId: string | undefined, progress?: CourseProgressLike) {
  const lessonIds = (module.lessons || []).map(lesson => lesson.id);
  const completed = new Set(progress?.completedLessonIds || []);
  const completedQuizIds = new Set(progress?.completedQuizIds || []);
  const lessonPct = lessonIds.length ? lessonIds.filter(id => completed.has(id)).length / lessonIds.length : 0;
  const quizPct = moduleQuizId && completedQuizIds.has(moduleQuizId) ? 1 : 0;
  return Math.round((lessonPct * 0.7 + quizPct * 0.3) * 100);
}
