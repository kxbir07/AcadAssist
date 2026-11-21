import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import { Check, ArrowRight, AlertTriangle } from 'lucide-react';
import HeroHeader from '../components/ui/HeroHeader';
import SectionHeader from '../components/ui/SectionHeader';
import ProgressBar from '../components/ui/ProgressBar';
import Modal from '../components/ui/Modal';
import { useApp } from '../context/AppContext';
import { calculateCourseProgress } from '../utils/courseProgress';

interface TopicMasteryRow {
  topic: string;
  accuracy: number;
  level: string;
}

export default function Progress() {
  const {
    studyGoals, toggleGoal, user, subjects, courses, courseProgress, quizzes, events, settings,
    performanceMetrics, quizAttempts, progressSummary
  } = useApp();
  const navigate = useNavigate();
  const [goals, setGoals] = useState(false);

  const active = courses.filter(c => c.enrolled).map(course => ({...course, summary: calculateCourseProgress(course, courseProgress[course.id]), displayColor: subjects.find(s => s.name === course.name)?.color || course.color}));
  const overall = active.length ? Math.round(active.reduce((sum, item) => sum + item.summary.overallPct, 0) / active.length) : 0;
  const completedQuizzes = quizzes.filter(q => q.score !== undefined);
  const courseQuizResults = active.flatMap(course => Object.values(courseProgress[course.id]?.quizResults || {}));
  const courseQuizScores = courseQuizResults.map(result => result.percentage);
  const avgScore = performanceMetrics && performanceMetrics.totalQuestionsAttempted > 0
    ? Math.round(performanceMetrics.overallAccuracy)
    : courseQuizScores.length
    ? Math.round(courseQuizScores.reduce((a, score) => a + score, 0) / courseQuizScores.length)
    : completedQuizzes.length
    ? Math.round(completedQuizzes.reduce((a, q) => a + (q.score || 0), 0) / completedQuizzes.length)
    : 0;
  const completedEvents = events.filter(e => e.completed).length;
  const totalEvents = events.length;
  const totalStudyHours = progressSummary?.studyTimeMinutes
    ? Number((progressSummary.studyTimeMinutes / 60).toFixed(1))
    : completedEvents;

  const weekly = useMemo(() => {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const map = days.map(day => ({ day, hours: 0 }));
    events
      .filter(e => e.type === 'Study Session' && e.completed)
      .forEach(e => {
        const d = new Date(e.date + 'T12:00:00').getDay();
        if (!Number.isNaN(d) && map[d]) {
          map[d].hours += 1;
        }
      });
    return map;
  }, [events]);

  const trend = useMemo(() => active.map(course => ({ course: course.name.length > 22 ? `${course.name.slice(0,22)}…` : course.name, progress: course.summary.overallPct })), [active]);

  const topicBreakdown = useMemo<TopicMasteryRow[]>(() => {
    const mapSource =
      (performanceMetrics?.topicMastery && Object.keys(performanceMetrics.topicMastery).length > 0
        ? performanceMetrics.topicMastery
        : progressSummary?.topicMastery) || {};
    return Object.entries(mapSource).map(([topic, rawVal]) => {
      const pct = rawVal <= 1 ? Math.round(rawVal * 100) : Math.round(rawVal);
      const level = pct >= 80 ? 'strong' : pct >= 60 ? 'developing' : 'weak';
      return { topic, accuracy: pct, level };
    });
  }, [performanceMetrics, progressSummary]);

  const weakTopics = useMemo<string[]>(() => {
    if (performanceMetrics?.weakTopics?.length) {
      return performanceMetrics.weakTopics.map(w => w.topic);
    }
    return topicBreakdown.filter((t: TopicMasteryRow) => t.accuracy < 60).map((t: TopicMasteryRow) => t.topic);
  }, [performanceMetrics, topicBreakdown]);

  const activity = [
    { name: 'Practice Quizzes', value: quizAttempts.length || completedQuizzes.length + courseQuizResults.length },
    { name: 'Planner Sessions', value: completedEvents },
    { name: 'Goals Completed', value: studyGoals.filter(g => g.completed).length },
  ];

  return (
    <div className="page-stack">
      <HeroHeader
        tag="YOUR PROGRESS"
        title={
          <>
            Small Steps. <span className="accent">Big Progress.</span>
          </>
        }
        subtitle="Curriculum analytics driven by the courses, practice quizzes, and planner activity in your workspace."
      />

      {/* Metrics Row (Workspace Metrics) */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <Stat value={`${overall}%`} label="Overall progress" sublabel="Workspace Average" />
        <Stat value={String(active.length)} label="Active subjects" sublabel="Curriculum" />
        <Stat value={`${avgScore}%`} label="Quiz average" sublabel="Diagnostic Score" />
        <Stat value={`${totalStudyHours}h`} label="Study time" sublabel={`${completedEvents}/${totalEvents} blocks done`} />
        <Stat value={`${user.streakDays} days`} label="Day streak" sublabel="Study Activity" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_1fr_280px] gap-6">
        <div>
          <SectionHeader icon="📊" title="Subject Progress" />
          <div className="card p-5 mb-6">
            {active.length ? (
              active.map(s => (
                <div key={s.id} className="flex items-center gap-3 mb-4 last:mb-0">
                  <div className="flex-1">
                    <div className="flex justify-between mb-1">
                      <span className="text-xs font-semibold">{s.name}</span>
                      <span className="text-xs font-bold">{s.summary.overallPct}%</span>
                    </div>
                    <ProgressBar value={s.summary.overallPct} color={s.displayColor} />
                    <small className="text-[.62rem] text-[var(--color-text-muted)]">
                      {s.summary.completedLessons}/{s.summary.totalLessons} lessons mastered
                    </small>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-inline">Enroll in courses to start tracking curriculum progress.</div>
            )}
          </div>

          <SectionHeader icon="📈" title="Progress Trend" />
          <div className="card p-5 mb-6">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-card-border)" />
                <XAxis dataKey="course" stroke="var(--color-text-muted)" fontSize={10} interval={0} angle={-20} textAnchor="end" height={55} />
                <YAxis domain={[0, 100]} unit="%" stroke="var(--color-text-muted)" fontSize={11} />
                <Tooltip contentStyle={{background:'var(--color-card-bg)',borderColor:'var(--color-card-border)',color:'var(--color-text-dark)',borderRadius:'8px',fontSize:'12px'}} />
                <Bar dataKey="progress" fill={settings.accentColor} radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
            <small className="text-[.62rem] text-[var(--color-text-muted)] block mt-2 text-right">* Current progress for each enrolled course</small>
          </div>

          <SectionHeader icon="🧠" title="Topic-Wise Mastery" />
          <div className="card p-5">
            {topicBreakdown.length ? (
              <div className="space-y-3">
                {topicBreakdown.slice(0, 8).map((t: TopicMasteryRow) => (
                  <div key={t.topic}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-semibold">{t.topic}</span>
                      <span className="font-bold">
                        {Math.round(t.accuracy)}% · <small className="uppercase">{t.level}</small>
                      </span>
                    </div>
                    <ProgressBar
                      value={Math.round(t.accuracy)}
                      color={t.accuracy >= 75 ? '#16a34a' : t.accuracy >= 50 ? settings.accentColor : '#dc2626'}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-inline">
                Complete a practice quiz in Assessment or Courses to populate topic-level mastery analytics.
              </div>
            )}
          </div>
        </div>

        <div>
          <SectionHeader icon="⏰" title="Study Activity Hours" />
          <div className="card p-5 mb-6">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={weekly}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-card-border)" />
                <XAxis dataKey="day" stroke="var(--color-text-muted)" fontSize={11} />
                <YAxis stroke="var(--color-text-muted)" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    background: 'var(--color-card-bg)',
                    borderColor: 'var(--color-card-border)',
                    color: 'var(--color-text-dark)',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="hours" fill={settings.accentColor} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <p className="muted text-xs mt-3">
              Tracked study sessions and completed planner blocks synchronized with backend analytics.
            </p>
          </div>

          <SectionHeader icon="🎯" title="Activity Mix" />
          <div className="card p-5 flex items-center gap-4 mb-6">
            <div className="w-36 h-36">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={activity} dataKey="value" innerRadius={38} outerRadius={60}>
                    {activity.map((_, i) => (
                      <Cell key={i} fill={[settings.accentColor, '#e07a5f', '#6366f1'][i % 3]} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex-1 space-y-2">
              {activity.map(a => (
                <div key={a.name} className="flex justify-between text-xs">
                  <span>{a.name}</span>
                  <b>{a.value}</b>
                </div>
              ))}
            </div>
          </div>

          <SectionHeader icon="⚠️" title="Weak-Topic Detection" />
          <div className="card p-5">
            {weakTopics.length ? (
              <div className="space-y-2">
                {weakTopics.map((topic: string) => (
                  <div key={topic} className="flex items-center justify-between gap-2 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/25">
                    <div className="flex items-center gap-2 text-xs font-semibold">
                      <AlertTriangle size={14} className="text-amber-600" />
                      <span>{topic}</span>
                    </div>
                    <button className="btn secondary text-xs" onClick={() => navigate('/assessment')}>
                      Practice
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-inline">
                No weak topics flagged below 60% mastery. Keep taking diagnostic quizzes to monitor your retention.
              </div>
            )}
          </div>
        </div>

        <div>
          <SectionHeader icon="🎯" title="Your Goals" action="View All" onAction={() => setGoals(true)} />
          <div className="card p-4 mb-6">
            {studyGoals.slice(0, 5).map(g => (
              <button
                key={g.id}
                className="w-full flex items-center gap-2 text-left py-2"
                onClick={() => toggleGoal(g.id)}
              >
                <span
                  className={`w-5 h-5 rounded-full border flex items-center justify-center flex-shrink-0 ${
                    g.completed ? 'bg-[var(--color-green-accent)] text-white' : ''
                  }`}
                >
                  {g.completed && <Check size={12} />}
                </span>
                <span
                  className={`text-xs ${
                    g.completed ? 'line-through text-[var(--color-text-muted)]' : ''
                  }`}
                >
                  {g.text}
                </span>
              </button>
            ))}
          </div>

          <div className="card p-5">
            <div className="section-kicker">NEXT STEP</div>
            <h3 className="mt-1">Turn weak progress into a scheduled action.</h3>
            <p className="muted text-xs mt-2 leading-relaxed">
              Use Planner to schedule focused study sessions for low-progress topics before exams.
            </p>
            <button className="btn primary mt-3 w-full" onClick={() => navigate('/planner')}>
              Open Planner <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>

      <Modal open={goals} onClose={() => setGoals(false)} title="All study goals">
        <div className="space-y-2">
          {studyGoals.map(g => (
            <button
              key={g.id}
              className="card w-full text-left p-3 flex items-center gap-2"
              onClick={() => toggleGoal(g.id)}
            >
              <span
                className={`w-5 h-5 rounded-full border flex items-center justify-center flex-shrink-0 ${
                  g.completed ? 'bg-[var(--color-green-accent)] text-white' : ''
                }`}
              >
                {g.completed && <Check size={12} />}
              </span>
              <b className={`text-xs ${g.completed ? 'line-through text-[var(--color-text-muted)]' : ''}`}>
                {g.text}
              </b>
            </button>
          ))}
        </div>
      </Modal>
    </div>
  );
}

function Stat({ value, label, sublabel }: { value: string; label: string; sublabel?: string }) {
  return (
    <div className="card p-4">
      <div className="text-lg font-black text-[var(--color-text-dark)]">{value}</div>
      <div className="text-[.68rem] text-[var(--color-text-muted)] font-medium mt-0.5">{label}</div>
      {sublabel && (
        <span className="text-[.6rem] text-[var(--color-text-muted)] opacity-75 block mt-0.5">
          {sublabel}
        </span>
      )}
    </div>
  );
}
