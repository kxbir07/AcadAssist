import { useState, useMemo, type CSSProperties } from 'react';
import {
  ArrowRight, CalendarDays, Check, FileText, Plus, Sparkles, Target, BookOpen,
  ChevronLeft, ChevronRight, AlertTriangle, Clock3, Flame, FileQuestion
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useApp, type CalendarEvent } from '../context/AppContext';
import Modal from '../components/ui/Modal';

const iso = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

export default function Dashboard() {
  const {
    user, todayPlan, togglePlanItem, courses, events, subjects, addEvent,
    pushToast, weakTopics, knowledgeMaterials, upcomingExams, performanceMetrics,
    studyRecommendation
  } = useApp();
  const navigate = useNavigate();
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [day, setDay] = useState(new Date());

  const enrolled = courses.filter(c => c.enrolled);
  const enrolledNames = new Set(enrolled.map(c => c.name));
  const activeSubjects = subjects.filter(s => enrolledNames.has(s.name) || enrolledNames.size === 0);
  const important = (activeSubjects.length ? activeSubjects : subjects).slice(0, 4);

  const upcomingEvents = events
    .filter(e => e.date >= iso(new Date()))
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(0, 5);

  const doneTasks = todayPlan.filter(x => x.status === 'completed').length;
  const overall = Math.round(enrolled.reduce((a, c) => a + c.progress, 0) / (enrolled.length || 1));
  const month = day.toLocaleString('en-US', { month: 'long', year: 'numeric' });
  const daysInMonth = new Date(day.getFullYear(), day.getMonth() + 1, 0).getDate();
  const firstDayIndex = new Date(day.getFullYear(), day.getMonth(), 1).getDay();

  const nextExam = useMemo(() => {
    const calendarExam = events
      .filter(e => e.type === 'Exam' && e.date >= iso(new Date()))
      .sort((a, b) => a.date.localeCompare(b.date))[0];

    const backendExam = upcomingExams && upcomingExams.length > 0 ? upcomingExams[0] : null;

    if (backendExam) {
      const nowMs = new Date().getTime();
      return {
        examName: backendExam.title,
        subject: backendExam.subjectId || 'Academic Subject',
        daysLeft: backendExam.daysUntilExam ?? Math.max(0, Math.ceil((new Date(backendExam.examDate).getTime() - nowMs) / (1000 * 60 * 60 * 24))),
        dateStr: new Date(backendExam.examDate).toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' }),
      };
    }
    if (calendarExam) {
      const nowMs = new Date().getTime();
      return {
        examName: calendarExam.title,
        subject: calendarExam.subject || 'Academic Subject',
        daysLeft: Math.max(0, Math.ceil((new Date(calendarExam.date + 'T00:00:00').getTime() - nowMs) / (1000 * 60 * 60 * 24))),
        dateStr: new Date(calendarExam.date + 'T00:00:00').toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' }),
      };
    }
    return null;
  }, [events, upcomingExams]);

  const recommendation = important[0] || subjects[0];

  const focus = () => {
    if (!recommendation) {
      navigate('/courses');
      return;
    }
    const date = iso(new Date());
    addEvent({
      id: crypto.randomUUID(),
      date,
      title: `Study ${recommendation.name}`,
      type: 'Study Session',
      subject: recommendation.name,
      time: 'Today',
      completed: false,
      notes: 'AI-recommended focus session targeted at weak areas and upcoming exam.',
    });
    pushToast('Recommended study session added to Planner');
    setAiOpen(false);
    navigate('/planner');
  };

  return (
    <div className="page-stack">
      {/* Top Hero Banner */}
      <div className="page-hero">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="eyebrow">STUDY COMMAND CENTER</span>
            <span className="soft-badge" style={{ fontSize: '0.62rem', padding: '2px 8px' }}>
              Personal Workspace
            </span>
          </div>
          <h1>
            {new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 18 ? 'Good afternoon' : 'Good evening'},{' '}
            <span>{user.name}.</span>
          </h1>
          <p>
            Track curriculum progress, strengthen identified weak topics, and prepare for upcoming exams.
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button className="btn secondary" onClick={() => navigate('/assessment')}>
            <Target size={15} /> Practice Quiz
          </button>
          <button className="btn primary" onClick={() => setAiOpen(true)}>
            <Sparkles size={16} /> What should I study?
          </button>
        </div>
      </div>

      <div className="dashboard-grid">
        <section className="dashboard-main">
          {/* Top Grid: Overall Progress + Today's Focus */}
          <div className="dashboard-top-grid">
            {/* Overall Progress Card */}
            <div className="card progress-wheel-card">
              <div className="flex justify-between items-start">
                <div>
                  <div className="section-kicker">OVERALL PROGRESS</div>
                  <h3>Curriculum Progress</h3>
                  <p className="muted text-xs">Across {enrolled.length} enrolled subjects</p>
                </div>
                <span className="soft-badge flex items-center gap-1">
                  <Flame size={12} className="text-orange-500" /> {user.streakDays}d streak
                </span>
              </div>
              <div className="progress-wheel" style={{ '--progress': `${overall}%` } as CSSProperties}>
                <div>
                  <strong>{overall}%</strong>
                  <span>complete</span>
                </div>
              </div>
              <div className="flex justify-between items-center text-xs text-[var(--color-text-muted)] pt-1 border-t border-[var(--color-border-light)]">
                <span>{subjects.reduce((a, s) => a + s.topicsCompleted, 0)} topics finished</span>
                <button className="link-btn" onClick={() => navigate('/progress')}>
                  View analytics <ArrowRight size={13} />
                </button>
              </div>
            </div>

            {/* Today's Focus Card */}
            <div className="card focus-card">
              <div className="section-title-row">
                <div>
                  <div className="section-kicker">TODAY'S STUDY FOCUS</div>
                  <h3>
                    {todayPlan.length > 0
                      ? `${todayPlan.length} task${todayPlan.length === 1 ? '' : 's'} · ${todayPlan.reduce((acc, t) => acc + (parseInt(t.duration || '0', 10) || 45), 0)}m planned`
                      : 'No tasks scheduled today'}
                  </h3>
                </div>
                <span className="soft-badge">
                  {doneTasks}/{todayPlan.length} done
                </span>
              </div>
              <div className="space-y-1 my-2">
                {todayPlan.length === 0 ? (
                  <div className="p-4 text-center text-xs text-[var(--color-text-muted)] flex flex-col items-center gap-1.5">
                    <span className="font-semibold text-[var(--color-text-dark)]">📅 Your study plan is empty for today</span>
                    <span>Create a study task to get started on today's curriculum.</span>
                    <button className="btn secondary text-xs mt-1" onClick={() => navigate('/planner')}>
                      <Plus size={13} /> Add Task
                    </button>
                  </div>
                ) : (
                  todayPlan.slice(0, 4).map(x => (
                    <div className="focus-item" key={x.id}>
                      <button
                        className={`check ${x.status === 'completed' ? 'done' : ''}`}
                        onClick={() => togglePlanItem(x.id)}
                        aria-label="Toggle task completion"
                      >
                        {x.status === 'completed' && <Check size={13} />}
                      </button>
                      <div>
                        <b>{x.title}</b>
                        <small>
                          {x.subject} · {x.time} ({x.duration})
                        </small>
                      </div>
                      <button
                        className="mini-btn"
                        onClick={() => navigate(`/planner?task=${encodeURIComponent(x.title)}`)}
                      >
                        Open
                      </button>
                    </div>
                  ))
                )}
              </div>
              <button className="full-btn" onClick={() => navigate('/planner')}>
                <Clock3 size={14} /> Open full study planner <ArrowRight size={14} />
              </button>
            </div>
          </div>

          {/* Upcoming Exam Highlight Banner */}
          {nextExam && (
            <div className="card p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-l-4 border-l-orange-500">
              <div className="flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-xl bg-orange-100 dark:bg-orange-950/40 text-orange-600 dark:text-orange-400 flex items-center justify-center flex-shrink-0">
                  <AlertTriangle size={20} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="eyebrow text-orange-600 dark:text-orange-400">UPCOMING EXAM ALERT</span>
                    <span className="px-2.5 py-0.5 rounded-full text-[.62rem] font-extrabold bg-orange-100 dark:bg-orange-950/60 text-orange-700 dark:text-orange-300 border border-orange-200 dark:border-orange-800/40">
                      {nextExam.daysLeft} days remaining
                    </span>
                  </div>
                  <h3 className="text-sm font-bold mt-0.5">{nextExam.examName}</h3>
                  <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                    Subject: <b>{nextExam.subject}</b> · Date: {nextExam.dateStr} · Recommended revision active
                  </p>
                </div>
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <button
                  className="btn secondary text-xs"
                  onClick={() => navigate(`/assessment?subject=${encodeURIComponent(nextExam.subject)}`)}
                >
                  <Target size={14} /> Practice questions
                </button>
                <button className="btn primary text-xs" onClick={() => navigate('/planner')}>
                  <CalendarDays size={14} /> View schedule
                </button>
              </div>
            </div>
          )}

          {/* Identified Weak Topics Section (Curriculum Intelligence via Service Layer) */}
          <div>
            <div className="section-title-row mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="section-kicker">ACADEMIC DIAGNOSTICS</span>
                  <span className="text-[.62rem] text-[var(--color-text-muted)] font-medium">
                    (Diagnostic Intelligence)
                  </span>
                </div>
                <h2 className="text-base font-bold">Identified Weak Topics</h2>
              </div>
              <button className="link-btn" onClick={() => navigate('/assessment')}>
                Take diagnostic quiz <ArrowRight size={14} />
              </button>
            </div>

            {weakTopics.length === 0 ? (
              <div className="card p-5 text-center text-xs text-[var(--color-text-muted)]">
                No weak topics detected yet. Complete practice quizzes in Assessment to identify focus areas.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {weakTopics.slice(0, 3).map(wt => (
                  <div key={wt.id} className="card p-3.5 flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start mb-1.5">
                        <span className="text-[.65rem] font-bold text-[var(--color-text-muted)] uppercase">
                          {wt.subject}
                        </span>
                        <span className="text-xs font-extrabold text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/40 px-2 py-0.5 rounded-md">
                          {wt.accuracyScore}% score
                        </span>
                      </div>
                      <b className="text-xs text-[var(--color-text-dark)] block leading-snug">{wt.topic}</b>
                      <p className="text-[.68rem] text-[var(--color-text-muted)] mt-1.5 leading-relaxed">
                        {wt.recommendedAction}
                      </p>
                    </div>
                    <button
                      className="btn secondary w-full text-xs mt-3"
                      onClick={() =>
                        navigate(
                          `/assessment?source=Topic&material=${encodeURIComponent(
                            wt.topic.split(' ')[0]
                          )}&subject=${encodeURIComponent(wt.subject)}`
                        )
                      }
                    >
                      <Target size={13} /> Practice this topic
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>


          {/* Important Subjects */}
          <div>
            <div className="section-title-row mb-3">
              <div>
                <div className="section-kicker">MY ENROLLED SUBJECTS</div>
                <h2 className="text-base font-bold">Keep these moving</h2>
              </div>
              <button className="link-btn" onClick={() => navigate('/courses')}>
                Manage subjects <ArrowRight size={14} />
              </button>
            </div>
            <div className="subject-grid">
              {important.map(s => {
                const c = courses.find(course => course.name === s.name);
                return (
                  <button
                    className="card subject-card text-left"
                    key={s.id}
                    onClick={() => navigate('/progress')}
                  >
                    <div
                      className="subject-icon"
                      style={{ background: `${s.color}18`, color: s.color }}
                    >
                      <BookOpen size={17} />
                    </div>
                    <div className="subject-head">
                      <b>{s.name}</b>
                      <span>{s.progress}%</span>
                    </div>
                    <div className="progress-track">
                      <span style={{ width: `${s.progress}%`, background: s.color }} />
                    </div>
                    <small>
                      {s.topicsCompleted}/{s.totalTopics} topics · {c?.estimatedHours || 32}h course
                    </small>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Recent Knowledge Materials Panel */}
          <div>
            <div className="section-title-row mb-3">
              <div>
                <div className="section-kicker">KNOWLEDGE BASE RECENT</div>
                <h2 className="text-base font-bold">Recent Course Documents</h2>
              </div>
              <button className="link-btn" onClick={() => navigate('/knowledge')}>
                All materials ({knowledgeMaterials.length}) <ArrowRight size={14} />
              </button>
            </div>
            {knowledgeMaterials.length === 0 ? (
              <div className="card p-6 text-center">
                <div className="text-3xl mb-2">📚</div>
                <h4 className="text-sm font-bold text-[var(--color-text-dark)]">No study material yet</h4>
                <p className="text-xs text-[var(--color-text-muted)] max-w-sm mx-auto mt-1 mb-3">
                  Upload your lecture notes or PDF to start building your knowledge base.
                </p>
                <button className="btn secondary text-xs" onClick={() => navigate('/knowledge')}>
                  <FileText size={14} /> Upload Document
                </button>
              </div>
            ) : (
              <div className="card p-2 divide-y divide-[var(--color-border-light)]">
                {knowledgeMaterials.slice(0, 3).map(m => (
                  <div key={m.id || m.name} className="flex items-center justify-between p-3 gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="w-8 h-8 rounded-lg bg-[var(--color-green-light)] text-[var(--color-green-accent)] flex items-center justify-center font-extrabold text-[.65rem] flex-shrink-0">
                        {m.type}
                      </span>
                      <div className="min-w-0">
                        <b className="text-xs text-[var(--color-text-dark)] truncate block">{m.name}</b>
                        <small className="text-[.65rem] text-[var(--color-text-muted)] block">
                          {m.subject} · {m.size} · Status: <span className="text-green-600 dark:text-green-400 font-semibold">{m.status}</span>
                        </small>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        className="btn subtle text-xs"
                        onClick={() => navigate(`/assessment?source=document&material=${encodeURIComponent(m.name)}`)}
                      >
                        <FileQuestion size={13} /> Quiz
                      </button>
                      <button
                        className="btn secondary text-xs"
                        onClick={() => navigate('/knowledge')}
                      >
                        View
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Upcoming Schedule */}
          <div>
            <div className="section-title-row mb-3">
              <div>
                <div className="section-kicker">SCHEDULE & DEADLINES</div>
                <h2 className="text-base font-bold">Upcoming academic events</h2>
              </div>
              <button className="link-btn" onClick={() => navigate('/planner')}>
                Open calendar <ArrowRight size={14} />
              </button>
            </div>
            <div className="upcoming-list card">
              {upcomingEvents.length ? (
                upcomingEvents.map(e => (
                  <button
                    className="upcoming-row w-full text-left"
                    key={e.id}
                    onClick={() => setSelectedEvent(e)}
                  >
                    <div className="event-date">
                      <strong>{new Date(e.date + 'T00:00:00').getDate()}</strong>
                      <small>
                        {new Date(e.date + 'T00:00:00').toLocaleString('en-US', { month: 'short' })}
                      </small>
                    </div>
                    <div className="flex-1 min-w-0">
                      <b className="truncate">{e.title}</b>
                      <small>
                        {e.subject || 'AcadAssist'} {e.time ? `· ${e.time}` : ''}
                      </small>
                    </div>
                    <span className="soft-badge flex-shrink-0">{e.type}</span>
                  </button>
                ))
              ) : (
                <div className="empty-inline p-4 text-center text-xs text-[var(--color-text-muted)] flex flex-col items-center gap-1.5">
                  <span>No upcoming academic events scheduled.</span>
                  <button className="btn secondary text-xs mt-1" onClick={() => navigate('/planner')}>
                    <CalendarDays size={13} /> Add Event
                  </button>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Aside / Sidebar Column */}
        <aside className="dashboard-side">
          {/* Calendar Widget */}
          <div className="card calendar-card">
            <div className="calendar-head">
              <button
                className="icon-button"
                onClick={() => setDay(new Date(day.getFullYear(), day.getMonth() - 1, 1))}
                aria-label="Previous month"
              >
                <ChevronLeft size={15} />
              </button>
              <strong>{month}</strong>
              <button
                className="icon-button"
                onClick={() => setDay(new Date(day.getFullYear(), day.getMonth() + 1, 1))}
                aria-label="Next month"
              >
                <ChevronRight size={15} />
              </button>
            </div>
            <div className="calendar-week">
              {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((d, i) => (
                <span key={i}>{d}</span>
              ))}
            </div>
            <div className="calendar-days">
              {Array.from({ length: firstDayIndex }).map((_, i) => (
                <span key={'x' + i} />
              ))}
              {Array.from({ length: daysInMonth }, (_, i) => i + 1).map(n => {
                const ds = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(
                  n
                ).padStart(2, '0')}`;
                const has = events.some(e => e.date === ds);
                const isToday = ds === iso(new Date());
                return (
                  <button
                    key={n}
                    className={`${isToday ? 'today ' : ''}${has ? 'has-event' : ''}`}
                    onClick={() => navigate(`/planner?date=${ds}`)}
                  >
                    {n}
                    {has && <i />}
                  </button>
                );
              })}
            </div>
            <button className="full-btn" onClick={() => navigate('/planner')}>
              <CalendarDays size={14} /> Open full calendar
            </button>
          </div>

          {/* AI Study Recommendation */}
          <div className="card ai-reco">
            <div className="flex justify-between items-start">
              <div className="ai-icon">
                <Sparkles size={18} />
              </div>
              <span className="text-[.6rem] font-bold bg-[var(--color-green-light)] text-[var(--color-green-accent)] px-2 py-0.5 rounded">
                Azure AI Ready
              </span>
            </div>
            <div className="section-kicker">AI STUDY RECOMMENDATION</div>
            <h3>What should you study next?</h3>
            <p>
              {studyRecommendation
                ? `Prioritize ${studyRecommendation.subjectName || 'Current Subject'}: ${studyRecommendation.reason}`
                : weakTopics.length > 0
                ? `Prioritize ${weakTopics[0].subject}: focus on ${weakTopics[0].topic} (${weakTopics[0].accuracyScore}% accuracy). ${weakTopics[0].recommendedAction}`
                : recommendation
                ? `Start with ${recommendation.name}: complete a topic module or take a practice quiz to generate personalized diagnostic focus.`
                : 'Enroll in courses to generate tailored study recommendations.'}
            </p>
            <div className="space-y-2 mt-3">
              <button
                className="btn primary w-full"
                onClick={focus}
                disabled={!recommendation}
              >
                <Clock3 size={14} /> Schedule 45 min focus block
              </button>
              <button
                className="btn secondary w-full text-xs"
                onClick={() => navigate('/assessment')}
              >
                <Target size={14} /> Test recall in Assessment
              </button>
            </div>
          </div>

          {/* Assessment Performance Diagnostic Widget */}
          <div className="card p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="section-kicker">PERFORMANCE SNAPSHOT</span>
              <span className="text-[.62rem] text-[var(--color-text-muted)]">
                {performanceMetrics && performanceMetrics.totalQuestionsAttempted > 0 ? 'Diagnostic Accuracy' : 'Live Workspace'}
              </span>
            </div>
            <div className="flex items-baseline gap-2 mb-2">
              <span className="text-2xl font-black text-[var(--color-text-dark)]">
                {performanceMetrics && performanceMetrics.totalQuestionsAttempted > 0
                  ? `${Math.round(performanceMetrics.overallAccuracy)}%`
                  : '0%'}
              </span>
              {performanceMetrics && performanceMetrics.totalQuestionsAttempted > 0 ? (
                <span className="text-xs text-green-600 font-bold">
                  {performanceMetrics.totalCorrect}/{performanceMetrics.totalQuestionsAttempted} correct
                </span>
              ) : (
                <span className="text-xs text-[var(--color-text-muted)] font-medium">No attempts yet</span>
              )}
            </div>
            <p className="text-xs text-[var(--color-text-muted)] mb-3">
              {performanceMetrics && performanceMetrics.totalQuestionsAttempted > 0
                ? `${performanceMetrics.totalQuestionsAttempted} practice questions solved across ${performanceMetrics.attemptCount} quiz attempt${performanceMetrics.attemptCount === 1 ? '' : 's'}.`
                : 'Solve practice questions in Assessment Studio to generate diagnostic mastery and performance trends.'}
            </p>
            <button className="full-btn" onClick={() => navigate('/assessment')}>
              <Target size={14} /> Open Assessment Studio
            </button>
          </div>

          {/* Quick Actions */}
          <div className="card quick-card">
            <div className="section-title-row mb-1">
              <h3>Quick Actions</h3>
              <Plus size={16} />
            </div>
            <button onClick={() => navigate('/knowledge')}>
              <FileText size={16} /> Upload study material <ArrowRight size={14} />
            </button>
            <button onClick={() => navigate('/assessment')}>
              <Target size={16} /> Generate practice quiz <ArrowRight size={14} />
            </button>
            <button onClick={() => navigate('/planner')}>
              <CalendarDays size={16} /> Schedule study session <ArrowRight size={14} />
            </button>
            <button onClick={() => navigate('/assistant')}>
              <Sparkles size={16} /> Ask AI Assistant a doubt <ArrowRight size={14} />
            </button>
          </div>
        </aside>
      </div>

      {/* Event Details Modal */}
      <Modal
        open={!!selectedEvent}
        onClose={() => setSelectedEvent(null)}
        title={selectedEvent?.title || 'Event'}
        subtitle={selectedEvent?.subject || 'Academic schedule'}
      >
        <p className="text-sm">
          {selectedEvent?.type} · {selectedEvent?.date}
          {selectedEvent?.time ? ` · ${selectedEvent.time}` : ''}
        </p>
        {selectedEvent?.notes && <p className="muted text-sm mt-2">{selectedEvent.notes}</p>}
        <div className="modal-actions">
          <button
            className="btn secondary"
            onClick={() => {
              setSelectedEvent(null);
              navigate('/planner');
            }}
          >
            Open planner
          </button>
          <button className="btn primary" onClick={focus}>
            Study this next
          </button>
        </div>
      </Modal>

      {/* AI Recommendation Modal */}
      <Modal
        open={aiOpen}
        onClose={() => setAiOpen(false)}
        title="What should I study today?"
        subtitle="Intelligent recommendation based on enrolled courses, weak topics, and upcoming exams"
      >
        <div className="text-sm space-y-2">
          {studyRecommendation ? (
            <p>
              Highest priority target: <b>{studyRecommendation.subjectName}</b> (<b>{studyRecommendation.topicName}</b>).{' '}
              {studyRecommendation.reason} A focused {studyRecommendation.suggestedDuration} revision session is recommended.
            </p>
          ) : recommendation ? (
            <p>
              Highest priority target: <b>{recommendation.name}</b>.
              {nextExam ? (
                <> Your upcoming exam <b>{nextExam.examName}</b> is in <b>{nextExam.daysLeft} days</b>.</>
              ) : null}
              {weakTopics.length > 0 ? (
                <> Your latest diagnostic score in <b>{weakTopics[0].topic}</b> is <b>{weakTopics[0].accuracyScore}%</b>. {weakTopics[0].recommendedAction}</>
              ) : (
                <> A focused 45-minute study session followed by a practice quiz will maintain your high curriculum momentum.</>
              )}
            </p>
          ) : (
            <p>Add a course from Courses first to enable study intelligence.</p>
          )}
        </div>
        <div className="modal-actions">
          <button
            className="btn secondary"
            onClick={() => {
              setAiOpen(false);
              navigate('/assessment');
            }}
          >
            Take practice quiz
          </button>
          <button className="btn primary" onClick={focus}>
            Schedule focus session
          </button>
        </div>
      </Modal>
    </div>
  );
}
