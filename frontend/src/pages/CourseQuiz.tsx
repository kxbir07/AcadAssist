import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle, ArrowLeft, Bookmark, Check, CheckCircle2, ChevronLeft,
  ChevronRight, Clock3, Lightbulb, RotateCcw, Timer, Trophy
} from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { useApp, type Course, type CourseQuiz } from '../context/AppContext';

function fallbackQuiz(c: Course): CourseQuiz {
  const topics = c.topics.length ? c.topics : ['Core concepts'];
  const questions = Array.from({ length: 30 }, (_, i) => {
    const topic = topics[i % topics.length];
    const distractors = topics.filter(t => t !== topic).slice(0, 3);
    while (distractors.length < 3) distractors.push('A topic outside the supplied course outline.');
    const options = [topic, ...distractors].slice(0, 4);
    const pos = (i * 5 + 1) % 4;
    [options[0], options[pos]] = [options[pos], options[0]];
    return {
      id: `${c.id}-fallback-q${i + 1}`,
      question: `Which course topic is explicitly included in the supplied ${c.name} outline? (Review item ${i + 1})`,
      options,
      correctIndex: pos,
      explanation: `${topic} is listed in the supplied course outline for ${c.name}.`,
      difficulty: (i % 3 === 0 ? 'Easy' : i % 3 === 1 ? 'Medium' : 'Hard') as 'Easy' | 'Medium' | 'Hard',
    };
  });
  return { id: `course-final-${c.id}`, courseId: c.id, title: `${c.name} — Final Quiz`, questions };
}

function formatSeconds(secs: number): string {
  const s = Math.max(0, Math.round(secs));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return m > 0 ? `${m}m ${String(r).padStart(2, '0')}s` : `${r}s`;
}

export default function CourseQuiz() {
  const { courseId, moduleId } = useParams();
  const navigate = useNavigate();
  const { courses, saveCourseQuizResult, courseProgress, pushToast } = useApp();
  const base = courses.find(c => c.id === courseId);
  const [course, setCourse] = useState<Course | undefined>(base);
  const [quiz, setQuiz] = useState<CourseQuiz | undefined>();
  const [loading, setLoading] = useState(true);
  const [answers, setAnswers] = useState<Record<string, number | null>>({});
  const [flagged, setFlagged] = useState<Record<string, boolean>>({});
  const [current, setCurrent] = useState(0);
  const [submitted, setSubmitted] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [resultId, setResultId] = useState<string | null>(null);
  const [timedMode, setTimedMode] = useState(false);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const startTimeRef = useRef<number>(Date.now());

  useEffect(() => {
    if (!courseId) return;
    let cancelled = false;
    const apply = (c: Course) => {
      if (cancelled) return;
      setCourse(c);
      const selected = moduleId
        ? (c.moduleQuizzes || []).find(q => q.moduleId === moduleId)
        : (c.finalQuiz || c.quiz);
      const activeQuiz = selected || (!moduleId ? fallbackQuiz(c) : undefined);
      setQuiz(activeQuiz);
      startTimeRef.current = Date.now();
      setElapsedSeconds(0);
      setRemainingSeconds((activeQuiz?.questions.length || 12) * 60);
      setLoading(false);
    };
    fetch(`/data/courses/${encodeURIComponent(courseId)}.json`)
      .then(r => (r.ok ? r.json() : Promise.reject(new Error('Course unavailable'))))
      .then((c: Course) => apply(c))
      .catch(() => {
        if (base) apply(base);
        else {
          setLoading(false);
          setQuiz(undefined);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [courseId, moduleId, base]);

  const questions = quiz?.questions || [];
  const q = questions[current];
  const answeredCount = useMemo(
    () => questions.filter(x => answers[x.id] !== null && answers[x.id] !== undefined).length,
    [questions, answers]
  );
  const unanswered = questions.length - answeredCount;
  const flaggedCount = useMemo(
    () => questions.filter(x => Boolean(flagged[x.id])).length,
    [questions, flagged]
  );
  const courseRecord = courseId ? courseProgress[courseId] : undefined;
  const completedQuizIds = courseRecord?.completedQuizIds || [];
  const quizResults = courseRecord?.quizResults || {};
  const priorResult = quiz ? quizResults[quiz.id] : undefined;

  const toggleFlag = useCallback((qId: string) => {
    setFlagged(prev => ({ ...prev, [qId]: !prev[qId] }));
  }, []);

  const submit = useCallback(() => {
    if (!quiz || submitted) return;
    const totalTime = Math.max(1, Math.round((Date.now() - startTimeRef.current) / 1000));
    setElapsedSeconds(totalTime);
    let correct = 0;
    questions.forEach(x => {
      if (answers[x.id] === x.correctIndex) correct++;
    });
    const total = questions.length;
    const incorrect = questions.filter(
      x => answers[x.id] !== null && answers[x.id] !== undefined && answers[x.id] !== x.correctIndex
    ).length;
    const result = {
      id: `${quiz.id}-${Date.now()}`,
      quizId: quiz.id,
      courseId: quiz.courseId,
      score: correct,
      total,
      percentage: total ? Math.round((correct / total) * 100) : 0,
      correct,
      incorrect,
      unanswered: total - correct - incorrect,
      answers,
      completedAt: new Date().toISOString(),
      quizType: (moduleId ? 'module' : 'final') as 'module' | 'final',
      moduleId,
      timeTakenSeconds: totalTime,
    };
    saveCourseQuizResult(result);
    setResultId(result.id);
    setConfirmOpen(false);
    setSubmitted(true);
    pushToast('Course quiz submitted and progress updated', 'success');
  }, [quiz, submitted, questions, answers, moduleId, saveCourseQuizResult, pushToast]);

  // Timer tick
  useEffect(() => {
    if (loading || submitted || !questions.length) return;
    const id = window.setInterval(() => {
      setElapsedSeconds(Math.max(1, Math.round((Date.now() - startTimeRef.current) / 1000)));
      if (timedMode) {
        setRemainingSeconds(prev => {
          if (prev <= 1) {
            submit();
            return 0;
          }
          return prev - 1;
        });
      }
    }, 1000);
    return () => window.clearInterval(id);
  }, [loading, submitted, questions.length, timedMode, submit]);

  // Keyboard shortcuts (1-4, A-D, Left/Right Arrow, F)
  useEffect(() => {
    if (loading || submitted || !q) return;
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        target?.isContentEditable
      ) {
        return;
      }

      if (e.key === 'ArrowRight') {
        e.preventDefault();
        setCurrent(i => Math.min(questions.length - 1, i + 1));
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setCurrent(i => Math.max(0, i - 1));
      } else if (e.key.toLowerCase() === 'f' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        toggleFlag(q.id);
      } else if (['1', '2', '3', '4'].includes(e.key) && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const idx = parseInt(e.key, 10) - 1;
        if (idx < q.options.length) {
          setAnswers(a => ({ ...a, [q.id]: idx }));
        }
      } else if (['a', 'b', 'c', 'd'].includes(e.key.toLowerCase()) && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const idx = e.key.toLowerCase().charCodeAt(0) - 97;
        if (idx < q.options.length) {
          setAnswers(a => ({ ...a, [q.id]: idx }));
        }
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [loading, submitted, q, questions.length, toggleFlag]);

  const difficultyStats = useMemo(() => {
    if (!submitted) return [];
    const stats: Record<string, { label: string; total: number; correct: number }> = {};
    for (const item of questions) {
      const diff = item.difficulty || 'Medium';
      if (!stats[diff]) stats[diff] = { label: diff, total: 0, correct: 0 };
      stats[diff].total += 1;
      if (answers[item.id] === item.correctIndex) stats[diff].correct += 1;
    }
    return Object.values(stats).map(s => ({
      ...s,
      accuracy: s.total ? Math.round((s.correct / s.total) * 100) : 0,
    }));
  }, [submitted, questions, answers]);

  if (loading)
    return (
      <div className="page-stack">
        <div className="content-card">Loading course quiz…</div>
      </div>
    );
  if (!course || !quiz)
    return (
      <div className="page-stack">
        <div className="empty-state">
          <h3>Course quiz unavailable</h3>
          <button className="btn secondary" onClick={() => navigate(`/courses/${courseId}`)}>
            Back to course
          </button>
        </div>
      </div>
    );
  if (!questions.length)
    return (
      <div className="page-stack">
        <div className="empty-state">
          <h3>No course quiz questions are available.</h3>
          <button className="btn secondary" onClick={() => navigate(`/courses/${courseId}`)}>
            Back to course
          </button>
        </div>
      </div>
    );

  if (submitted) {
    const r = (resultId ? quizResults[quiz.id] : undefined) || priorResult;
    return (
      <div className="page-stack">
        <div className="page-hero">
          <div>
            <div className="eyebrow">{moduleId ? 'MODULE QUIZ RESULT' : 'FINAL COURSE QUIZ RESULT'}</div>
            <h1>{quiz.title}</h1>
            <p>
              Completed in {formatSeconds(r?.timeTakenSeconds ?? elapsedSeconds)} · Accuracy:{' '}
              {r?.percentage ?? 0}%
            </p>
          </div>
          <Trophy size={42} />
        </div>
        <div className="stats-grid">
          <div className="stat-card">
            <strong>{r?.percentage ?? 0}%</strong>
            <span>Accuracy Score</span>
          </div>
          <div className="stat-card">
            <strong>{r?.correct ?? 0}</strong>
            <span>Correct</span>
          </div>
          <div className="stat-card">
            <strong>{r?.incorrect ?? 0}</strong>
            <span>Incorrect</span>
          </div>
          <div className="stat-card">
            <strong>{r?.unanswered ?? 0}</strong>
            <span>Unanswered</span>
          </div>
        </div>

        {difficultyStats.length > 0 && (
          <div className="content-card">
            <div className="section-heading">
              <div>
                <div className="eyebrow">PERFORMANCE BREAKDOWN</div>
                <h2>Difficulty-wise accuracy</h2>
              </div>
              <span className="soft-badge">Time: {formatSeconds(r?.timeTakenSeconds ?? elapsedSeconds)}</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {difficultyStats.map(ds => (
                <div key={ds.label} className="p-3 rounded-xl border border-[var(--color-card-border)] flex justify-between items-center text-xs">
                  <b>{ds.label} Questions</b>
                  <span>
                    {ds.correct}/{ds.total} ({ds.accuracy}%)
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="content-card">
          <div className="section-heading">
            <div>
              <div className="eyebrow">REVIEW</div>
              <h2>Question-wise solutions & explanations</h2>
            </div>
          </div>
          <div className="quiz-review-list">
            {questions.map((x, i) => {
              const userChoice = answers[x.id];
              const isCorrect = userChoice === x.correctIndex;
              return (
                <div className="quiz-review-item" key={x.id}>
                  <div>
                    <strong>
                      {i + 1}. {x.question}
                    </strong>
                    <p>
                      Your answer:{' '}
                      <b>
                        {userChoice === null || userChoice === undefined
                          ? 'Not answered'
                          : `${String.fromCharCode(65 + userChoice)}. ${x.options[userChoice]}`}
                      </b>{' '}
                      {isCorrect ? '✓' : '✗'}
                    </p>
                    <p className="success-text">
                      Correct: {String.fromCharCode(65 + x.correctIndex)}. {x.options[x.correctIndex]}
                    </p>
                    <p className="flex items-start gap-1.5 mt-1">
                      <Lightbulb size={14} className="mt-0.5 flex-shrink-0" />
                      <span>{x.explanation}</span>
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="modal-actions">
            <button className="btn secondary" onClick={() => navigate(`/courses/${courseId}`)}>
              <ArrowLeft size={15} />
              Back to Course
            </button>
            <button
              className="btn primary"
              onClick={() => {
                startTimeRef.current = Date.now();
                setElapsedSeconds(0);
                setRemainingSeconds(questions.length * 60);
                setAnswers({});
                setFlagged({});
                setCurrent(0);
                setSubmitted(false);
                setResultId(null);
              }}
            >
              <RotateCcw size={15} />
              Retry Quiz
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <div className="page-hero">
        <div>
          <button className="link-btn" onClick={() => navigate(`/courses/${courseId}`)}>
            <ArrowLeft size={15} />
            Back to Course
          </button>
          <div className="eyebrow">
            {moduleId ? 'MODULE QUIZ' : 'FINAL COURSE QUIZ'} · {questions.length} QUESTIONS
          </div>
          <h1>{quiz.title}</h1>
          <p>
            Use keyboard shortcuts (1-4 or A-D to select, ←/→ to navigate, F to flag) or click below.
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className={`btn ${timedMode ? 'primary' : 'secondary'} text-xs`}
              onClick={() => setTimedMode(t => !t)}
            >
              <Timer size={14} /> {timedMode ? 'Timed Mode ON' : 'Enable Timer'}
            </button>
            <span className="soft-badge flex items-center gap-1">
              <Clock3 size={13} />
              {timedMode
                ? `${Math.floor(remainingSeconds / 60)}:${String(remainingSeconds % 60).padStart(2, '0')}`
                : formatSeconds(elapsedSeconds)}
            </span>
          </div>
          <span className="text-xs muted">
            {answeredCount}/{questions.length} answered · {flaggedCount} flagged
          </span>
        </div>
      </div>

      <div className="quiz-layout">
        <aside className="quiz-nav card p-4">
          <div className="section-kicker">QUESTION NAVIGATOR</div>
          <div className="quiz-number-grid">
            {questions.map((x, i) => (
              <button
                key={x.id}
                className={`quiz-number ${i === current ? 'active' : ''} ${
                  answers[x.id] !== undefined && answers[x.id] !== null ? 'answered' : ''
                }`}
                style={flagged[x.id] ? { outline: '2px solid #f59e0b', position: 'relative' } : undefined}
                onClick={() => setCurrent(i)}
                title={`Question ${i + 1}${flagged[x.id] ? ' (Flagged)' : ''}`}
              >
                {i + 1}
              </button>
            ))}
          </div>
          <p className="muted text-xs mt-3">
            {unanswered} unanswered · {flaggedCount} flagged{' '}
            {completedQuizIds?.includes(quiz.id) ? '· Previously completed' : ''}
          </p>
          <button className="btn primary w-full mt-3 text-xs" onClick={() => setConfirmOpen(true)}>
            <CheckCircle2 size={14} /> Submit Assessment
          </button>
        </aside>

        <div className="content-card quiz-panel">
          <div className="flex justify-between items-center gap-4 mb-5">
            <div>
              <span className="soft-badge">{q?.difficulty || 'Mixed'}</span>
              <div className="eyebrow mt-3">
                QUESTION {current + 1} OF {questions.length}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {q && (
                <button
                  type="button"
                  className={`flag-btn ${flagged[q.id] ? 'flagged' : ''}`}
                  onClick={() => toggleFlag(q.id)}
                  title="Flag or unflag question (Shortcut: F)"
                >
                  <Bookmark size={14} fill={flagged[q.id] ? 'currentColor' : 'none'} />
                  <span>{flagged[q.id] ? 'Flagged' : 'Flag'}</span>
                </button>
              )}
              <span className="muted text-sm">{Math.round(((current + 1) / questions.length) * 100)}%</span>
            </div>
          </div>
          <div className="progress-track">
            <span style={{ width: `${((current + 1) / questions.length) * 100}%` }} />
          </div>
          <h2 className="mt-6 text-xl font-bold leading-relaxed">{q?.question}</h2>
          <div className="quiz-options mt-6" role="radiogroup" aria-label="Answer options">
            {q?.options.map((option, i) => {
              const isSelected = answers[q.id] === i;
              return (
                <button
                  key={`${q.id}-${i}`}
                  className={`quiz-option ${isSelected ? 'selected' : ''}`}
                  onClick={() => setAnswers(a => ({ ...a, [q.id]: i }))}
                  role="radio"
                  aria-checked={isSelected}
                >
                  <span className="quiz-option-index">{String.fromCharCode(65 + i)}</span>
                  <span className="flex-1">{option}</span>
                  {isSelected && <Check size={15} />}
                </button>
              );
            })}
          </div>
          <div className="modal-actions mt-8 justify-between">
            <button
              className="btn secondary"
              disabled={current === 0}
              onClick={() => setCurrent(x => Math.max(0, x - 1))}
            >
              <ChevronLeft size={16} />
              Previous
            </button>
            <div className="text-xs muted hidden sm:block">
              Shortcuts: <b>1-4</b> / <b>A-D</b> select · <b>←/→</b> navigate · <b>F</b> flag
            </div>
            {current < questions.length - 1 ? (
              <button
                className="btn primary"
                onClick={() => setCurrent(x => Math.min(questions.length - 1, x + 1))}
              >
                Next
                <ChevronRight size={16} />
              </button>
            ) : (
              <button className="btn primary" onClick={() => setConfirmOpen(true)}>
                <CheckCircle2 size={15} /> Review & Submit
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Confirmation Dialog */}
      {confirmOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/55 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="Confirm course quiz submission"
          onClick={() => setConfirmOpen(false)}
        >
          <div
            className="bg-[var(--color-card-bg)] border border-[var(--color-card-border)] rounded-2xl max-w-md w-full p-6 shadow-2xl flex flex-col gap-4 text-left"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/15 text-amber-600 flex items-center justify-center flex-none mt-0.5">
                <AlertCircle size={22} />
              </div>
              <div>
                <h3 className="text-base font-bold text-[var(--color-text-dark)] m-0">
                  Submit Course Examination?
                </h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-1 mb-0 leading-relaxed">
                  You have answered <b>{answeredCount}</b> of <b>{questions.length}</b> questions ({unanswered}{' '}
                  unanswered, {flaggedCount} flagged).
                </p>
              </div>
            </div>

            {unanswered > 0 && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800">
                ⚠️ <b>{unanswered}</b> question{unanswered > 1 ? 's are' : ' is'} unanswered and will count as incorrect.
              </div>
            )}

            {flaggedCount > 0 && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl text-xs text-blue-800">
                📌 <b>{flaggedCount}</b> question{flaggedCount > 1 ? 's are' : ' is'} flagged for review.
              </div>
            )}

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-[var(--color-border-light)]">
              <button className="btn secondary text-xs" onClick={() => setConfirmOpen(false)}>
                Keep Working
              </button>
              <button className="btn primary text-xs" onClick={submit}>
                <CheckCircle2 size={14} /> Submit Now
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
