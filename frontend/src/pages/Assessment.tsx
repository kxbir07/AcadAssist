import { useEffect, useState, useCallback, useMemo } from 'react';
import {
  CheckCircle2, FileQuestion, History, RotateCcw, Sparkles, Target, X, Clock3,
  AlertCircle, AlertTriangle, ArrowRight, ArrowLeft, Bookmark, Check,
  BookOpen, Timer, Lightbulb, Layers
} from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useApp, type Quiz } from '../context/AppContext';
import Modal from '../components/ui/Modal';
import { generateQuiz, submitQuiz, isDocumentReady, formatApiError } from '../services/api';

const TOPICS = [
  'Deadlocks',
  'CPU Scheduling',
  'Memory Management',
  'Transport Layer',
  'Application Layer',
  'Normalization',
  'B+ Trees & Indexing',
  'Graph Traversals (BFS/DFS)',
  'Linear Regression',
];

type AssessmentSource = 'Topic' | 'Subject' | 'Knowledge' | 'Notes' | 'Weak Topics';

export default function Assessment() {
  const {
    subjects, knowledgeMaterials, notes, quizzes, addQuiz, updateQuiz,
    pushToast, weakTopics, quizAttempts, reloadAppData
  } = useApp();
  const [params] = useSearchParams();

  const initialSourceParam = params.get('source');
  const initialSource: AssessmentSource =
    initialSourceParam === 'document'
      ? 'Knowledge'
      : initialSourceParam === 'notes'
      ? 'Notes'
      : initialSourceParam === 'subject'
      ? 'Subject'
      : initialSourceParam === 'weak'
      ? 'Weak Topics'
      : 'Topic';

  const [source, setSource] = useState<AssessmentSource>(initialSource);
  const [subject, setSubject] = useState(params.get('subject') || subjects[0]?.name || 'Operating Systems');
  const [topic, setTopic] = useState(params.get('material') || 'Deadlocks');
  const [selectedDocId, setSelectedDocId] = useState<string>(
    params.get('document_id') || params.get('docId') || ''
  );
  const [difficulty, setDifficulty] = useState<Quiz['difficulty']>('Mixed');
  const [count, setCount] = useState(10);
  const [mode, setMode] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [active, setActive] = useState<Quiz | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [result, setResult] = useState<number | null>(null);
  const [showReview, setShowReview] = useState(false);
  const [history, setHistory] = useState(false);
  const [timer, setTimer] = useState(0);
  const [confirm, setConfirm] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [flagged, setFlagged] = useState<Record<string, boolean>>({});
  const [navFilter, setNavFilter] = useState<'all' | 'unanswered' | 'flagged'>('all');
  const [solutionFilter, setSolutionFilter] = useState<'all' | 'incorrect' | 'flagged'>('all');

  useEffect(() => {
    if (source === 'Knowledge' && knowledgeMaterials.length > 0) {
      const targetParam = params.get('document_id') || params.get('material');
      const match = targetParam
        ? knowledgeMaterials.find(m => m.id === targetParam || m.name.toLowerCase().includes(targetParam.toLowerCase()))
        : null;
      if (match) {
        setSelectedDocId(match.id || '');
        setTopic(match.name);
        if (match.subject) {
          const matchingSubject = subjects.find(s => s.name.toLowerCase() === match.subject.toLowerCase() || s.id.toLowerCase() === (match.subjectId || '').toLowerCase());
          if (matchingSubject) setSubject(matchingSubject.name);
        }
      } else if (!selectedDocId || !knowledgeMaterials.some(m => m.id === selectedDocId)) {
        const firstDoc = knowledgeMaterials[0];
        setSelectedDocId(firstDoc.id || '');
        setTopic(firstDoc.name);
        if (firstDoc.subject) {
          const matchingSubject = subjects.find(s => s.name.toLowerCase() === firstDoc.subject.toLowerCase() || s.id.toLowerCase() === (firstDoc.subjectId || '').toLowerCase());
          if (matchingSubject) setSubject(matchingSubject.name);
        }
      }
    }
  }, [source, knowledgeMaterials, params, selectedDocId, subjects]);

  useEffect(() => {
    if (!active) return;
    document.body.classList.add('quiz-active');
    return () => document.body.classList.remove('quiz-active');
  }, [active]);

  useEffect(() => {
    if (!mode || result !== null || timer <= 0) return;
    const id = window.setInterval(() => setTimer(t => Math.max(0, t - 1)), 1000);
    return () => window.clearInterval(id);
  }, [mode, result, timer]);

  const toggleFlag = useCallback((id: string) => {
    setFlagged(f => ({ ...f, [id]: !f[id] }));
  }, []);

  const clearCurrentAnswer = useCallback((id: string) => {
    setAnswers(prev => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }, []);

  const sourceItems =
    source === 'Knowledge'
      ? knowledgeMaterials.map(x => x.name)
      : source === 'Notes'
      ? notes.map(x => x.title)
      : source === 'Subject'
      ? subjects.map(s => s.name)
      : source === 'Weak Topics'
      ? weakTopics.map(w => w.topic)
      : TOPICS;

  const closeQuiz = () => {
    setActive(null);
    setAnswers({});
    setResult(null);
    setCurrentQuestion(0);
    setTimer(0);
    setConfirm(false);
    setShowReview(false);
    setMobileNav(false);
    setFlagged({});
    setNavFilter('all');
    setSolutionFilter('all');
  };

  const startQuizAsync = async (options: {
    targetTopic?: string;
    targetSubject?: string;
    documentId?: string;
    isExam?: boolean;
    count?: number;
    difficulty?: Quiz['difficulty'];
    sourceType?: AssessmentSource;
  }) => {
    const reqTopic = options.targetTopic || topic;
    const reqSubject = options.targetSubject || subject;
    const reqExam = options.isExam ?? mode;
    const reqCount = options.count ?? count;
    const reqDiff = options.difficulty ?? difficulty;
    const reqSource = options.sourceType ?? source;
    const docId = options.documentId ?? (reqSource === 'Knowledge' ? (selectedDocId || knowledgeMaterials[0]?.id) : undefined);
    const targetDoc = docId ? knowledgeMaterials.find(m => m.id === docId) : undefined;
    const finalSubject = (reqSource === 'Knowledge' && targetDoc?.subject) ? targetDoc.subject : reqSubject;

    const subjObj = subjects.find(s => s.name.toLowerCase() === finalSubject.toLowerCase() || s.id.toLowerCase() === (targetDoc?.subjectId || finalSubject).toLowerCase());
    const subjectId = targetDoc?.subjectId || subjObj?.id || finalSubject.toLowerCase().replace(/\s+/g, '_');
    const courseId = targetDoc?.courseId || subjObj?.code || subjObj?.id || 'cs';

    setGenerating(true);
    setGenError(null);

    try {
      const quizData = await generateQuiz({
        documentId: docId,
        courseId: courseId,
        subjectId: subjectId,
        subject: reqSubject,
        topic: reqTopic,
        difficulty: reqDiff,
        count: reqCount,
        sourceType: reqSource,
        isExam: reqExam,
      });

      const q: Quiz = {
        id: quizData.id,
        title: quizData.title,
        source: quizData.source,
        subject: quizData.subject,
        difficulty: reqDiff,
        questions: quizData.questions,
      };

      addQuiz(q);
      setActive(q);
      setAnswers({});
      setResult(null);
      setCurrentQuestion(0);
      setShowReview(false);
      setTimer(reqExam ? reqCount * 60 : 0);
      setMode(reqExam);
      setMobileNav(false);
      setFlagged({});
      setNavFilter('all');
      setSolutionFilter('all');
      pushToast(`Quiz generated for ${reqTopic}`);
    } catch (err: any) {
      console.error('Quiz generation failed:', err);
      const errMsg = formatApiError(err, 'Failed to generate assessment questions. Please try again.');
      setGenError(errMsg);
      pushToast(errMsg, 'error');
    } finally {
      setGenerating(false);
    }
  };

  const startQuizFromTopic = (targetTopic: string, targetSubject = 'Operating Systems', isExam = false) => {
    startQuizAsync({
      targetTopic,
      targetSubject,
      isExam,
      count: 5,
      sourceType: 'Topic',
    });
  };

  const generate = () => {
    const selectedItem = source === 'Knowledge' ? topic : source === 'Topic' || source === 'Weak Topics' ? topic : sourceItems[0] || 'Deadlocks';
    startQuizAsync({
      targetTopic: selectedItem,
      targetSubject: subject,
      isExam: mode,
      count: count,
      difficulty: difficulty,
      sourceType: source,
      documentId: source === 'Knowledge' ? (selectedDocId || knowledgeMaterials[0]?.id) : undefined,
    });
  };

  const submit = useCallback(async () => {
    if (!active) return;
    setConfirm(false);
    setShowReview(false);

    try {
      const submissionAnswers = active.questions.map(q => {
        const selectedIdx = answers[q.id];
        const selectedText = selectedIdx !== undefined && q.options[selectedIdx] ? q.options[selectedIdx] : '';
        return {
          questionId: q.id,
          selectedAnswer: selectedText,
          timeTaken: 10,
        };
      });

      const submissionResult = await submitQuiz(active.id, submissionAnswers);

      const score = Math.round(submissionResult.percentage);
      setResult(score);

      // Re-hydrate questions with backend-evaluated answers and explanations
      if (submissionResult.questionResults && submissionResult.questionResults.length > 0) {
        const resultMap = new Map(submissionResult.questionResults.map(r => [r.questionId, r]));
        const updatedQuestions = active.questions.map(q => {
          const resItem = resultMap.get(q.id);
          if (resItem) {
            const correctText = resItem.correctAnswer.trim().toLowerCase();
            const correctIdx = q.options.findIndex(opt => {
              const optClean = opt.trim().toLowerCase();
              return (
                optClean === correctText ||
                (correctText.length >= 2 && optClean.startsWith(correctText.slice(0, 2))) ||
                (optClean.length >= 2 && correctText.startsWith(optClean.slice(0, 2))) ||
                (correctText.length > 3 && optClean.includes(correctText)) ||
                (optClean.length > 3 && correctText.includes(optClean))
              );
            });
            return {
              ...q,
              answer: correctIdx !== -1 ? correctIdx : 0,
              explanation: resItem.explanation || q.explanation,
            };
          }
          return q;
        });

        const updatedQuiz = { ...active, questions: updatedQuestions, score, completedAt: new Date().toISOString() };
        setActive(updatedQuiz);
        updateQuiz(active.id, { score, completedAt: new Date().toISOString(), questions: updatedQuestions });
      } else {
        updateQuiz(active.id, { score, completedAt: new Date().toISOString() });
      }

      pushToast(`Quiz submitted — ${score}%`);
    } catch (err: any) {
      console.warn('Backend quiz attempt submission error:', err);
      const correct = active.questions.filter(q => q.answer >= 0 && answers[q.id] === q.answer).length;
      const score = Math.round((correct / active.questions.length) * 100);
      updateQuiz(active.id, { score, completedAt: new Date().toISOString() });
      setResult(score);
      pushToast(`Quiz submitted — ${score}%`);
    }

    reloadAppData();
  }, [active, answers, updateQuiz, pushToast, reloadAppData]);

  interface DisplayAttempt {
    id: string;
    topic: string;
    subject: string;
    percentage: string;
    scoreFraction: string;
    date: string;
    isPassed: boolean;
    isExcellent: boolean;
  }

  const userAttempts: DisplayAttempt[] = useMemo(() => {
    if (quizAttempts && quizAttempts.length > 0) {
      return quizAttempts.map(a => ({
        id: a.attemptId,
        topic: a.title,
        subject: a.subject,
        percentage: `${Math.round(a.percentage)}%`,
        scoreFraction: `${a.score} / ${a.total}`,
        date: a.completedAt ? new Date(a.completedAt).toLocaleDateString() : 'Recently',
        isPassed: a.percentage >= 70,
        isExcellent: a.percentage >= 85,
      }));
    }
    const completedLocal = quizzes.filter(q => q.score !== undefined);
    return completedLocal.map(q => ({
      id: q.id,
      topic: q.title,
      subject: q.subject,
      percentage: `${q.score}%`,
      scoreFraction: `${Math.round(((q.score || 0) * q.questions.length) / 100)} / ${q.questions.length}`,
      date: q.completedAt ? new Date(q.completedAt).toLocaleDateString() : 'Today',
      isPassed: (q.score || 0) >= 70,
      isExcellent: (q.score || 0) >= 85,
    }));
  }, [quizAttempts, quizzes]);

  useEffect(() => {
    if (active && mode && result === null && timer === 0) submit();
  }, [timer, active, mode, result, submit]);

  const retry = () => {
    if (!active) return;
    setAnswers({});
    setResult(null);
    setCurrentQuestion(0);
    setShowReview(false);
    setTimer(mode ? active.questions.length * 60 : 0);
    setFlagged({});
    setNavFilter('all');
    setSolutionFilter('all');
  };

  const jumpTo = (index: number) => {
    setCurrentQuestion(index);
    setMobileNav(false);
  };

  // Keyboard navigation for power users
  useEffect(() => {
    if (!active || result !== null) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      const currQ = active.questions[currentQuestion];
      if (!currQ) return;

      if (e.key === 'ArrowRight') {
        setCurrentQuestion(i => Math.min(active.questions.length - 1, i + 1));
      } else if (e.key === 'ArrowLeft') {
        setCurrentQuestion(i => Math.max(0, i - 1));
      } else if (e.key.toLowerCase() === 'f') {
        toggleFlag(currQ.id);
      } else if (['1', '2', '3', '4'].includes(e.key)) {
        const idx = parseInt(e.key, 10) - 1;
        if (idx < currQ.options.length) {
          setAnswers(a => ({ ...a, [currQ.id]: idx }));
        }
      } else if (['a', 'b', 'c', 'd'].includes(e.key.toLowerCase())) {
        const idx = e.key.toLowerCase().charCodeAt(0) - 97;
        if (idx < currQ.options.length) {
          setAnswers(a => ({ ...a, [currQ.id]: idx }));
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [active, result, currentQuestion, toggleFlag]);

  const question = active?.questions[currentQuestion];
  const answeredCount = active ? Object.keys(answers).length : 0;
  const unanswered = active ? active.questions.length - answeredCount : 0;
  const flaggedCount = active ? active.questions.filter(q => flagged[q.id]).length : 0;
  const progressPercent = active && active.questions.length > 0 ? Math.round((answeredCount / active.questions.length) * 100) : 0;

  return (
    <div className="page-stack">
      {/* Hero Header */}
      <div className="page-hero">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="eyebrow">AI ASSESSMENT STUDIO</span>
            <span className="soft-badge" style={{ fontSize: '0.62rem', padding: '2px 8px' }}>
              Deterministic Engine · Azure Foundry Ready
            </span>
          </div>
          <h1>Practice what matters.</h1>
          <p>
            Generate targeted quizzes from subjects, uploaded course materials, notes, or your identified weak topics.
          </p>
        </div>
        <button className="btn secondary" onClick={() => setHistory(true)}>
          <History size={16} /> Quiz history ({quizzes.length})
        </button>
      </div>

      {/* Main Generator Layout */}
      <div className="assessment-layout">
        {/* Left: Generator Form */}
        <div className="card generator-card">
          <div className="section-kicker">CREATE AN ASSESSMENT</div>
          <h2>AI Quiz Generator</h2>
          <p className="muted text-xs">
            Select a curriculum source to generate multiple-choice questions with step-by-step explanations.
          </p>

          <div className="source-tabs mt-4">
            {(['Topic', 'Subject', 'Knowledge', 'Notes', 'Weak Topics'] as const).map(s => (
              <button
                key={s}
                className={source === s ? 'active' : ''}
                onClick={() => {
                  setSource(s);
                  setGenError(null);
                  if (s === 'Knowledge') {
                    if (knowledgeMaterials.length > 0) {
                      setSelectedDocId(knowledgeMaterials[0].id || '');
                      setTopic(knowledgeMaterials[0].name);
                    }
                  } else {
                    const items =
                      s === 'Notes'
                        ? notes.map(x => x.title)
                        : s === 'Subject'
                        ? subjects.map(sub => sub.name)
                        : s === 'Weak Topics'
                        ? weakTopics.map(w => w.topic)
                        : TOPICS;
                    setTopic(items[0] || 'Deadlocks');
                  }
                }}
              >
                <FileQuestion size={14} />
                <span>{s}</span>
              </button>
            ))}
          </div>

          <label>
            Subject
            <select className="select full" value={subject} onChange={e => setSubject(e.target.value)}>
              {subjects.map(s => (
                <option key={s.id}>{s.name}</option>
              ))}
            </select>
          </label>

          <label>
            Target {source}
            {source === 'Knowledge' ? (
              <select
                className="select full"
                value={selectedDocId || (knowledgeMaterials[0]?.id ?? '')}
                onChange={e => {
                  const newId = e.target.value;
                  setSelectedDocId(newId);
                  const m = knowledgeMaterials.find(x => x.id === newId);
                  if (m) {
                    setTopic(m.name);
                    if (m.subject) {
                      const matchingSubject = subjects.find(s => s.name.toLowerCase() === m.subject.toLowerCase() || s.id.toLowerCase() === (m.subjectId || '').toLowerCase());
                      if (matchingSubject) setSubject(matchingSubject.name);
                    }
                  }
                }}
              >
                {knowledgeMaterials.length === 0 ? (
                  <option value="">No uploaded documents found</option>
                ) : (
                  knowledgeMaterials.map(m => (
                    <option key={m.id} value={m.id}>
                      {m.name}{isDocumentReady(m.rawStatus) ? '' : ` (${m.status})`}
                    </option>
                  ))
                )}
              </select>
            ) : (
              <select className="select full" value={topic} onChange={e => setTopic(e.target.value)}>
                {sourceItems.map(x => (
                  <option key={x} value={x}>{x}</option>
                ))}
              </select>
            )}
          </label>

          <div className="form-grid">
            <label>
              Questions
              <select className="select full" value={count} onChange={e => setCount(Number(e.target.value))}>
                {[5, 10, 15, 20].map(n => (
                  <option key={n} value={n}>{n} questions</option>
                ))}
              </select>
            </label>
            <label>
              Difficulty
              <select
                className="select full"
                value={difficulty}
                onChange={e => setDifficulty(e.target.value as Quiz['difficulty'])}
              >
                {['Easy', 'Medium', 'Hard', 'Mixed', 'Adaptive'].map(x => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
          </div>

          <label className="toggle-row">
            <input type="checkbox" checked={mode} onChange={e => setMode(e.target.checked)} />
            <span>
              <b>Timed Exam Mode</b>
              <small>Simulates official test conditions with countdown timer and final score review.</small>
            </span>
          </label>

          {(() => {
            const selectedMaterial = source === 'Knowledge'
              ? knowledgeMaterials.find(m => m.id === (selectedDocId || knowledgeMaterials[0]?.id))
              : undefined;
            const docNotReady = source === 'Knowledge' && !!selectedMaterial && !isDocumentReady(selectedMaterial.rawStatus);
            return (
              <>
                {docNotReady && (
                  <div className="mt-3 p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/40 rounded-lg flex items-start gap-2.5 text-xs text-amber-800 dark:text-amber-300">
                    <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" />
                    <span>
                      <b>{selectedMaterial?.name}</b> is not ready yet ({selectedMaterial?.status}). Wait for
                      processing to finish before generating a quiz from it.
                    </span>
                  </div>
                )}
                <button
                  className="btn primary large w-full mt-2"
                  onClick={generate}
                  disabled={generating || (source === 'Knowledge' && (knowledgeMaterials.length === 0 || docNotReady))}
                >
                  <Sparkles size={17} className={generating ? 'animate-spin' : ''} />
                  {generating ? 'Generating questions with AI...' : 'Generate assessment'}
                </button>
              </>
            );
          })()}

          {genError && (
            <div className="mt-3 p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/40 rounded-lg flex items-start gap-2.5 text-xs text-red-700 dark:text-red-300">
              <AlertCircle size={16} className="flex-shrink-0 mt-0.5 text-red-500" />
              <div>
                <b className="block font-semibold">Assessment Generation Notice</b>
                <span>{genError}</span>
              </div>
            </div>
          )}
        </div>

        {/* Right: Intelligence Overview */}
        <div className="card how-card">
          <div className="ai-icon">
            <Sparkles size={18} />
          </div>
          <h3>Assessment Intelligence</h3>
          <p className="muted text-xs mb-3">
            Every completed quiz feeds your weak topic diagnostics and updates the Study Planner.
          </p>

          {[
            'Select any course topic or uploaded document',
            'Take in untimed practice or timed exam mode',
            'Full navigation to flag and skip questions',
            'Instant score review with detailed explanations',
            'Weak topics dynamically populate revision tasks',
          ].map(x => (
            <div className="feature-row" key={x}>
              <CheckCircle2 size={16} />
              <span>{x}</span>
            </div>
          ))}

          <div className="callout mt-4">
            <b>AI Grounding Active:</b> Assessments generated from Knowledge documents are dynamically created using Azure AI Search retrieval and Microsoft Foundry (gpt-4.1-mini) strictly from your uploaded materials.
          </div>
        </div>
      </div>

      {/* Recommended Assessments Section (Based on Real AcadAssist Data) */}
      <div>
        <div className="section-title-row mb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="section-kicker">RECOMMENDED FOR YOU</span>
              <span className="text-[.62rem] text-[var(--color-text-muted)]">Curriculum Diagnostics</span>
            </div>
            <h2 className="text-base font-bold">Recommended Practice Targets</h2>
          </div>
        </div>

        {weakTopics.length === 0 ? (
          <div className="card p-6 text-center">
            <div className="text-3xl mb-2">📝</div>
            <h3 className="text-sm font-bold text-[var(--color-text-dark)]">No assessments available yet</h3>
            <p className="text-xs text-[var(--color-text-muted)] max-w-sm mx-auto mt-1 mb-3">
              Generate and complete your first practice quiz above to detect focus areas and track score progress.
            </p>
            <button
              className="btn primary text-xs"
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            >
              <Target size={14} /> Start Assessment
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {weakTopics.map(wt => (
              <div key={wt.id} className="card p-4 flex flex-col justify-between border-t-2 border-t-[var(--color-green-accent)]">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <span className="soft-badge text-[.65rem]">{wt.subject}</span>
                    <span className="text-xs font-bold text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/40 px-2 py-0.5 rounded">
                      {wt.accuracyScore}% score
                    </span>
                  </div>
                  <h3 className="text-sm font-bold">{wt.topic}</h3>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1.5 leading-relaxed">
                    {wt.recommendedAction}
                  </p>
                  {wt.examName && (
                    <div className="flex items-center gap-1.5 text-xs text-orange-600 dark:text-orange-400 font-semibold mt-2.5">
                      <AlertTriangle size={13} /> {wt.examName} in {wt.daysToExam} days
                    </div>
                  )}
                </div>
                <div className="flex gap-2 mt-4">
                  <button
                    className="btn primary flex-1 text-xs"
                    onClick={() => startQuizFromTopic(wt.topic.split(' ')[0], wt.subject, false)}
                  >
                    <Target size={14} /> Practice
                  </button>
                  <button
                    className="btn secondary text-xs"
                    onClick={() => startQuizFromTopic(wt.topic.split(' ')[0], wt.subject, true)}
                  >
                    <Clock3 size={13} /> Timed
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Attempts and Practice History */}
      <div>
        <div className="section-title-row mb-3">
          <div>
            <div className="section-kicker">PRACTICE ATTEMPTS</div>
            <h2 className="text-base font-bold">Recent Assessment Performance</h2>
          </div>
          <button className="link-btn" onClick={() => setHistory(true)}>
            View all history <ArrowRight size={14} />
          </button>
        </div>

        {userAttempts.length === 0 ? (
          <div className="card p-5 text-center text-xs text-[var(--color-text-muted)]">
            No recent quiz attempts recorded yet. Select any topic above and click &quot;Generate assessment&quot; to test your knowledge.
          </div>
        ) : (
          <div className="card p-2 divide-y divide-[var(--color-border-light)]">
            {userAttempts.map((att) => (
              <div key={att.id} className="flex items-center justify-between p-3 gap-3">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center font-bold text-xs ${
                      att.isExcellent
                        ? 'bg-green-100 text-green-700 dark:bg-green-950/50 dark:text-green-400'
                        : att.isPassed
                        ? 'bg-blue-100 text-blue-700 dark:bg-blue-950/50 dark:text-blue-400'
                        : 'bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-400'
                    }`}
                  >
                    {att.percentage}
                  </div>
                  <div>
                    <b className="text-xs text-[var(--color-text-dark)] block">{att.topic}</b>
                    <small className="text-[.65rem] text-[var(--color-text-muted)]">
                      Subject: {att.subject} · Score: {att.scoreFraction} · Date: {att.date}
                    </small>
                  </div>
                </div>
                <button
                  className="btn subtle text-xs"
                  onClick={() => startQuizFromTopic(att.topic.split(' ')[0], att.subject, false)}
                >
                  <RotateCcw size={13} /> Retry topic
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Active Full-Screen Quiz Experience */}
      {active && (
        <div className="quiz-shell" role="dialog" aria-modal="true" aria-label={active.title}>
          {/* Top Animated Progress Bar */}
          <div className="quiz-top-progress">
            <div
              className="quiz-top-progress-fill"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          <header className="quiz-shell-head">
            <div className="quiz-title-wrap">
              <button className="quiz-exit-btn" onClick={closeQuiz} aria-label="Exit quiz" title="Exit Quiz">
                <X size={18} />
              </button>
              <div>
                <div className="flex items-center gap-2 mb-0.5">
                  <span className={`quiz-mode-pill ${mode ? 'timed' : 'practice'}`}>
                    {mode ? <Timer size={11} /> : <BookOpen size={11} />}
                    {mode ? 'Timed Exam Mode' : 'Practice Mode'}
                  </span>
                  <span className="text-[0.68rem] font-semibold text-[var(--color-text-muted)]">
                    {active.subject}
                  </span>
                </div>
                <h2 className="text-base md:text-lg font-bold text-[var(--color-text-dark)] truncate max-w-[260px] sm:max-w-md">
                  {active.title}
                </h2>
              </div>
            </div>

            <div className="quiz-header-meta">
              <div className="quiz-stat-chip hidden sm:inline-flex">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>
                  <b>{answeredCount}</b> of {active.questions.length} answered
                </span>
                <span className="text-xs text-[var(--color-green-accent)] font-extrabold ml-1">
                  ({progressPercent}%)
                </span>
              </div>

              {mode && result === null && (
                <div className={`timer-chip ${timer <= 60 ? 'warning' : ''}`}>
                  <Clock3 size={14} />
                  <span>
                    {Math.floor(timer / 60)}:{String(timer % 60).padStart(2, '0')}
                  </span>
                </div>
              )}

              {result === null && (
                <button
                  className="btn subtle text-xs hidden md:inline-flex"
                  onClick={() => setConfirm(true)}
                >
                  <CheckCircle2 size={14} className="text-emerald-600" />
                  Submit
                </button>
              )}
            </div>
          </header>

          {result === null ? (
            <div className="quiz-body">
              <main className="quiz-content">
                <div className="quiz-center-column">
                  <div className="quiz-card">
                    <div className="quiz-card-head">
                      <div className="flex items-center gap-2">
                        <span className="question-badge">
                          Question {currentQuestion + 1} of {active.questions.length}
                        </span>
                        {answers[question?.id || ''] !== undefined && (
                          <span className="inline-flex items-center gap-1 text-[0.68rem] font-bold text-emerald-700 bg-emerald-50 dark:bg-emerald-950/40 dark:text-emerald-400 px-2 py-0.5 rounded-md">
                            <Check size={11} /> Saved
                          </span>
                        )}
                      </div>

                      <div className="question-actions-group">
                        {question && answers[question.id] !== undefined && (
                          <button
                            className="clear-btn"
                            onClick={() => clearCurrentAnswer(question.id)}
                            title="Clear selection for this question"
                          >
                            Clear answer
                          </button>
                        )}
                        {question && (
                          <button
                            className={`flag-btn ${flagged[question.id] ? 'flagged' : ''}`}
                            onClick={() => toggleFlag(question.id)}
                            title="Flag for later review"
                          >
                            <Bookmark size={13} fill={flagged[question.id] ? 'currentColor' : 'none'} />
                            <span>{flagged[question.id] ? 'Flagged' : 'Flag'}</span>
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="question-text">
                      {question?.text}
                    </div>

                    <div className="option-stack" role="radiogroup" aria-label="Answer options">
                      {question?.options.map((optionText, j) => {
                        const isSelected = answers[question.id] === j;
                        const letter = String.fromCharCode(65 + j);
                        return (
                          <button
                            key={`${question.id}-${j}`}
                            className={`option-item ${isSelected ? 'selected' : ''}`}
                            onClick={() => setAnswers(a => ({ ...a, [question.id]: j }))}
                            role="radio"
                            aria-checked={isSelected}
                          >
                            <div className="option-letter">{letter}</div>
                            <div className="option-label">{optionText}</div>
                            <div className="option-check">
                              {isSelected && <Check size={13} strokeWidth={3} />}
                            </div>
                            <span className="option-key-badge hidden sm:inline-block">
                              {j + 1}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Navigation controls */}
                  <div className="quiz-controls-row">
                    <button
                      className="btn secondary"
                      onClick={() => setCurrentQuestion(i => Math.max(0, i - 1))}
                      disabled={currentQuestion === 0}
                    >
                      <ArrowLeft size={14} /> Previous
                    </button>

                    <div className="quiz-kbd-hints hidden md:flex">
                      <span><kbd>1</kbd>-<kbd>4</kbd> or <kbd>A</kbd>-<kbd>D</kbd> select</span>
                      <span>•</span>
                      <span><kbd>←</kbd> <kbd>→</kbd> navigate</span>
                      <span>•</span>
                      <span><kbd>F</kbd> flag</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        className="btn secondary mobile-question-btn"
                        onClick={() => setMobileNav(true)}
                      >
                        <Layers size={14} /> Questions ({answeredCount}/{active.questions.length})
                      </button>

                      {currentQuestion < active.questions.length - 1 ? (
                        <button
                          className="btn primary"
                          onClick={() => setCurrentQuestion(i => Math.min(active.questions.length - 1, i + 1))}
                        >
                          Next <ArrowRight size={14} />
                        </button>
                      ) : (
                        <button className="btn primary" onClick={() => setConfirm(true)}>
                          <CheckCircle2 size={15} /> Review & Submit
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </main>

              {/* Modern Question Navigator Sidebar */}
              <aside className={`quiz-nav-sidebar ${mobileNav ? 'open' : ''}`} aria-label="Question navigation">
                <div className="quiz-nav-header">
                  <div className="quiz-nav-title-row">
                    <div>
                      <b className="text-sm font-bold text-[var(--color-text-dark)]">Question Navigator</b>
                      <small className="block text-[0.66rem] text-[var(--color-text-muted)]">
                        Click any number to jump
                      </small>
                    </div>
                    <button
                      className="icon-button question-nav-close"
                      onClick={() => setMobileNav(false)}
                      aria-label="Close question navigation"
                    >
                      <X size={16} />
                    </button>
                  </div>

                  <div className="quiz-nav-stats-pills">
                    <div className="quiz-stat-box">
                      <b className="text-emerald-700 dark:text-emerald-400">{answeredCount}</b>
                      <small>Answered</small>
                    </div>
                    <div className="quiz-stat-box">
                      <b className="text-amber-600 dark:text-amber-400">{flaggedCount}</b>
                      <small>Flagged</small>
                    </div>
                    <div className="quiz-stat-box">
                      <b className="text-[var(--color-text-muted)]">{unanswered}</b>
                      <small>Left</small>
                    </div>
                  </div>

                  {/* Filter tabs */}
                  <div className="quiz-filter-chips">
                    <button
                      className={`quiz-filter-chip ${navFilter === 'all' ? 'active' : ''}`}
                      onClick={() => setNavFilter('all')}
                    >
                      All ({active.questions.length})
                    </button>
                    <button
                      className={`quiz-filter-chip ${navFilter === 'unanswered' ? 'active' : ''}`}
                      onClick={() => setNavFilter('unanswered')}
                    >
                      Left ({unanswered})
                    </button>
                    <button
                      className={`quiz-filter-chip ${navFilter === 'flagged' ? 'active' : ''}`}
                      onClick={() => setNavFilter('flagged')}
                    >
                      Flagged ({flaggedCount})
                    </button>
                  </div>
                </div>

                {/* 5-Column Question Grid */}
                <div className="quiz-nav-grid-modern">
                  {active.questions.map((q, i) => {
                    const isAnswered = answers[q.id] !== undefined;
                    const isCurrent = i === currentQuestion;
                    const isFlagged = Boolean(flagged[q.id]);

                    let dimmed = false;
                    if (navFilter === 'unanswered' && isAnswered) dimmed = true;
                    if (navFilter === 'flagged' && !isFlagged) dimmed = true;

                    return (
                      <button
                        key={q.id}
                        className={`nav-grid-btn ${isCurrent ? 'current' : ''} ${
                          isAnswered ? 'answered' : ''
                        } ${isFlagged ? 'flagged-mark' : ''}`}
                        style={{ opacity: dimmed ? 0.35 : 1 }}
                        onClick={() => jumpTo(i)}
                        aria-label={`Question ${i + 1}${isCurrent ? ' current' : ''}${isAnswered ? ' answered' : ''}${isFlagged ? ' flagged' : ''}`}
                      >
                        {i + 1}
                        {isFlagged && <span className="flag-dot" />}
                      </button>
                    );
                  })}
                </div>

                <div className="quiz-nav-legend">
                  <div>
                    <span className="w-2.5 h-2.5 rounded-sm bg-[var(--color-green-accent)] inline-block" />
                    <span>Current Question</span>
                  </div>
                  <div>
                    <span className="w-2.5 h-2.5 rounded-sm bg-[#eef8f2] border border-[#b3dfc6] inline-block" />
                    <span>Answered ({answeredCount})</span>
                  </div>
                  <div>
                    <span className="w-2.5 h-2.5 rounded-sm bg-amber-400 inline-block" />
                    <span>Flagged for review ({flaggedCount})</span>
                  </div>
                  <div>
                    <span className="w-2.5 h-2.5 rounded-sm border border-[var(--color-card-border)] bg-[var(--color-card-bg)] inline-block" />
                    <span>Unanswered ({unanswered})</span>
                  </div>
                </div>

                <div className="sidebar-submit-card">
                  <div className="flex items-center justify-between text-xs font-bold text-[var(--color-text-dark)]">
                    <span>Ready to submit?</span>
                    <span className="text-[var(--color-green-accent)]">{progressPercent}% done</span>
                  </div>
                  <p>
                    {unanswered > 0
                      ? `${unanswered} question${unanswered > 1 ? 's' : ''} still unanswered.`
                      : 'All questions completed!'}
                  </p>
                  <button className="btn primary w-full text-xs" onClick={() => setConfirm(true)}>
                    <CheckCircle2 size={14} /> Submit Quiz
                  </button>
                </div>
              </aside>

              {mobileNav && (
                <button
                  className="question-nav-overlay"
                  aria-label="Close navigation"
                  onClick={() => setMobileNav(false)}
                />
              )}
            </div>
          ) : (
            /* Result Screen */
            <div className="quiz-result-wrapper">
              <div className="quiz-result-container">
                <div className="result-hero-card">
                  <div
                    className={`result-score-circle ${
                      result >= 80 ? 'excellent' : result >= 60 ? 'good' : 'needs-work'
                    }`}
                  >
                    <span className="text-3xl font-black">{result}%</span>
                    <span className="text-[0.65rem] font-bold uppercase tracking-wider mt-0.5">Score</span>
                  </div>

                  <div className="eyebrow">ASSESSMENT COMPLETED</div>
                  <h2 className="text-xl md:text-2xl font-bold font-serif mt-1">
                    {result >= 80
                      ? 'Exceptional Mastery! 🌟'
                      : result >= 60
                      ? 'Solid Understanding 👍'
                      : 'Targeted Review Recommended 🎯'}
                  </h2>
                  <p className="text-xs text-[var(--color-text-muted)] max-w-lg mx-auto mt-2 leading-relaxed">
                    You answered <b>{active.questions.filter(q => answers[q.id] === q.answer).length}</b> of{' '}
                    <b>{active.questions.length}</b> questions correctly.
                    {result < 70 && ' We have marked key concepts in your study planner to reinforce your understanding.'}
                  </p>

                  <div className="result-metric-grid mt-6">
                    <div className="result-metric-card">
                      <b className="text-emerald-600 dark:text-emerald-400">
                        {active.questions.filter(q => answers[q.id] === q.answer).length}
                      </b>
                      <span>Correct</span>
                    </div>
                    <div className="result-metric-card">
                      <b className="text-rose-600 dark:text-rose-400">
                        {active.questions.filter(q => answers[q.id] !== undefined && answers[q.id] !== q.answer).length}
                      </b>
                      <span>Incorrect</span>
                    </div>
                    <div className="result-metric-card">
                      <b className="text-amber-600 dark:text-amber-400">
                        {unanswered}
                      </b>
                      <span>Skipped</span>
                    </div>
                    <div className="result-metric-card">
                      <b className="text-[var(--color-text-dark)]">
                        {active.questions.length}
                      </b>
                      <span>Total Questions</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-center gap-3 mt-6">
                    <button className="btn secondary text-xs" onClick={retry}>
                      <RotateCcw size={14} /> Retake Quiz
                    </button>
                    <button
                      className="btn secondary text-xs"
                      onClick={() => setShowReview(v => !v)}
                    >
                      <Target size={14} /> {showReview ? 'Hide Solutions' : 'Review Solutions'}
                    </button>
                    <button
                      className="btn primary text-xs"
                      onClick={() => {
                        closeQuiz();
                        generate();
                      }}
                    >
                      <Sparkles size={14} /> Next Practice Set
                    </button>
                    <button className="btn subtle text-xs" onClick={closeQuiz}>
                      <X size={14} /> Exit Assessment
                    </button>
                  </div>
                </div>

                {showReview && (
                  <div className="flex flex-col gap-4">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <h3 className="text-base font-bold text-[var(--color-text-dark)]">
                        Question & Solution Breakdown
                      </h3>
                      <div className="quiz-filter-chips">
                        <button
                          className={`quiz-filter-chip ${solutionFilter === 'all' ? 'active' : ''}`}
                          onClick={() => setSolutionFilter('all')}
                        >
                          All ({active.questions.length})
                        </button>
                        <button
                          className={`quiz-filter-chip ${solutionFilter === 'incorrect' ? 'active' : ''}`}
                          onClick={() => setSolutionFilter('incorrect')}
                        >
                          Incorrect Only (
                          {active.questions.filter(q => answers[q.id] !== q.answer).length}
                          )
                        </button>
                        <button
                          className={`quiz-filter-chip ${solutionFilter === 'flagged' ? 'active' : ''}`}
                          onClick={() => setSolutionFilter('flagged')}
                        >
                          Flagged ({flaggedCount})
                        </button>
                      </div>
                    </div>

                    <div className="grid gap-3">
                      {active.questions
                        .filter(q => {
                          if (solutionFilter === 'incorrect') return answers[q.id] !== q.answer;
                          if (solutionFilter === 'flagged') return Boolean(flagged[q.id]);
                          return true;
                        })
                        .map((q, i) => {
                          const isCorrect = answers[q.id] === q.answer;
                          const isUnanswered = answers[q.id] === undefined;

                          return (
                            <div className="solution-card" key={q.id}>
                              <div className="solution-header">
                                <span className="font-bold text-xs text-[var(--color-text-dark)]">
                                  Q{i + 1}. {q.text}
                                </span>
                                <span
                                  className={`solution-status-badge ${
                                    isCorrect
                                      ? 'correct'
                                      : isUnanswered
                                      ? 'unanswered'
                                      : 'incorrect'
                                  }`}
                                >
                                  {isCorrect ? '✓ Correct' : isUnanswered ? 'Skipped' : '✗ Incorrect'}
                                </span>
                              </div>

                              <div className="solution-answers-box">
                                <div className="flex items-start gap-2">
                                  <span className="text-[var(--color-text-muted)] font-semibold w-24 flex-none">
                                    Your Choice:
                                  </span>
                                  <span
                                    className={`font-semibold ${
                                      isCorrect
                                        ? 'text-emerald-600 dark:text-emerald-400'
                                        : isUnanswered
                                        ? 'text-gray-500'
                                        : 'text-rose-600 dark:text-rose-400'
                                    }`}
                                  >
                                    {isUnanswered
                                      ? 'Not answered'
                                      : `${String.fromCharCode(65 + answers[q.id])}. ${q.options[answers[q.id]]}`}
                                  </span>
                                </div>
                                {!isCorrect && (
                                  <div className="flex items-start gap-2">
                                    <span className="text-[var(--color-text-muted)] font-semibold w-24 flex-none">
                                      Correct Answer:
                                    </span>
                                    <span className="font-bold text-emerald-700 dark:text-emerald-400">
                                      {String.fromCharCode(65 + q.answer)}. {q.options[q.answer]}
                                    </span>
                                  </div>
                                )}
                              </div>

                              {q.explanation && (
                                <div className="solution-explanation">
                                  <Lightbulb size={16} className="text-emerald-600 flex-none mt-0.5" />
                                  <div>
                                    <b className="block text-xs font-bold text-[var(--color-text-dark)] mb-0.5">
                                      Explanation & Concept
                                    </b>
                                    <p className="m-0 text-[0.74rem] text-[var(--color-text-body)]">
                                      {q.explanation}
                                    </p>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Submit Confirmation Dialog inside Quiz Shell */}
          {confirm && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/55 backdrop-blur-sm"
              role="dialog"
              aria-modal="true"
              aria-label="Confirm quiz submission"
              onClick={() => setConfirm(false)}
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
                      Submit Assessment?
                    </h3>
                    <p className="text-xs text-[var(--color-text-muted)] mt-1 mb-0 leading-relaxed">
                      You have answered <b>{answeredCount}</b> of <b>{active.questions.length}</b> questions. Once submitted, your score will be calculated and saved.
                    </p>
                  </div>
                </div>

                {unanswered > 0 && (
                  <div className="p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/40 rounded-xl text-xs text-amber-800 dark:text-amber-300">
                    ⚠️ <b>{unanswered}</b> question{unanswered > 1 ? 's are' : ' is'} unanswered and will count as incorrect.
                  </div>
                )}

                {flaggedCount > 0 && (
                  <div className="p-3 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800/40 rounded-xl text-xs text-blue-800 dark:text-blue-300">
                    📌 <b>{flaggedCount}</b> question{flaggedCount > 1 ? 's are' : ' is'} flagged for review.
                  </div>
                )}

                <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-[var(--color-border-light)]">
                  <button
                    className="btn secondary text-xs"
                    onClick={() => setConfirm(false)}
                  >
                    Keep Working
                  </button>
                  <button
                    className="btn primary text-xs"
                    onClick={() => {
                      setConfirm(false);
                      submit();
                    }}
                  >
                    <CheckCircle2 size={14} /> Submit Assessment
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Quiz History Modal */}
      <Modal open={history} onClose={() => setHistory(false)} title="Quiz History" wide>
        <div>
          {quizzes.length ? (
            quizzes.map(q => (
              <div className="history-row" key={q.id}>
                <div>
                  <b>{q.title}</b>
                  <small>
                    {q.subject} · {q.difficulty} · {q.questions.length} questions ·{' '}
                    {q.completedAt ? new Date(q.completedAt).toLocaleDateString() : 'Draft'}
                  </small>
                </div>
                <span className="font-extrabold text-sm">{q.score === undefined ? 'Not attempted' : `${q.score}%`}</span>
                <button
                  className="btn subtle text-xs"
                  onClick={() => {
                    setActive(q);
                    setAnswers({});
                    setResult(null);
                    setCurrentQuestion(0);
                    setShowReview(false);
                    setTimer(0);
                    setHistory(false);
                  }}
                >
                  Retake
                </button>
              </div>
            ))
          ) : (
            <div className="empty-inline">
              No assessments generated yet. Select a topic above to create your first quiz.
            </div>
          )}
        </div>
      </Modal>

      {/* Submit Confirmation Modal */}
      <Modal open={confirm} onClose={() => setConfirm(false)} title="Submit assessment" subtitle="You cannot change answers after submitting.">
        <div className="flex items-start gap-3">
          <AlertCircle size={20} className="text-amber-600" />
          <p className="text-sm">
            You have answered <b>{answeredCount}</b> of {active?.questions.length || 0} questions.{' '}
            {unanswered > 0 ? (
              <>
                <b>{unanswered}</b> question{unanswered > 1 ? 's are' : ' is'} unanswered and will count as incorrect.
              </>
            ) : (
              <>All questions are answered.</>
            )}{' '}
            Submit now?
          </p>
        </div>
        <div className="modal-actions">
          <button className="btn secondary" onClick={() => setConfirm(false)}>
            Keep working
          </button>
          <button className="btn primary" onClick={submit}>
            Submit now
          </button>
        </div>
      </Modal>
    </div>
  );
}
