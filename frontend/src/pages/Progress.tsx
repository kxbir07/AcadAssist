import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area
} from 'recharts';
import { Check, ArrowRight } from 'lucide-react';
import HeroHeader from '../components/ui/HeroHeader';
import SectionHeader from '../components/ui/SectionHeader';
import ProgressBar from '../components/ui/ProgressBar';
import Modal from '../components/ui/Modal';
import { useApp } from '../context/AppContext';

export default function Progress() {
  const {
    studyGoals, toggleGoal, user, subjects, courses, quizzes, events, settings,
    performanceMetrics, quizAttempts
  } = useApp();
  const navigate = useNavigate();
  const [goals, setGoals] = useState(false);

  const active = subjects.filter(s => courses.some(c => c.enrolled && c.name === s.name));
  const overall = Math.round(active.reduce((a, s) => a + s.progress, 0) / (active.length || 1));
  const completedQuizzes = quizzes.filter(q => q.score !== undefined);
  const avgScore = performanceMetrics && performanceMetrics.totalQuestionsAttempted > 0
    ? Math.round(performanceMetrics.overallAccuracy)
    : completedQuizzes.length
    ? Math.round(completedQuizzes.reduce((a, q) => a + (q.score || 0), 0) / completedQuizzes.length)
    : 0;
  const completedEvents = events.filter(e => e.completed).length;
  const totalEvents = events.length;

  const weekly = useMemo(() => {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const map = days.map(day => ({ day, hours: 0 }));
    events
      .filter(e => e.type === 'Study Session' && e.completed)
      .forEach(e => {
        const d = new Date(e.date + 'T12:00:00').getDay();
        map[d].hours += 1;
      });
    return map;
  }, [events]);

  const trend = useMemo(() => {
    const base = Math.max(0, overall - 20);
    return Array.from({ length: 5 }, (_, i) => ({
      week: `W${i + 1}`,
      progress: Math.min(overall, base + Math.round(((overall - base) * (i + 1)) / 5)),
    }));
  }, [overall]);

  const activity = [
    { name: 'Practice Quizzes', value: quizAttempts.length || completedQuizzes.length },
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
        <Stat value={`${completedEvents}/${totalEvents}`} label="Planner events done" sublabel="Scheduled" />
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
                      <span className="text-xs font-bold">{s.progress}%</span>
                    </div>
                    <ProgressBar value={s.progress} color={s.color} />
                    <small className="text-[.62rem] text-[var(--color-text-muted)]">
                      {s.topicsCompleted}/{s.totalTopics} topics mastered
                    </small>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-inline">Enroll in courses to start tracking curriculum progress.</div>
            )}
          </div>

          <SectionHeader icon="📈" title="Progress Trend" />
          <div className="card p-5">
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-card-border)" />
                <XAxis dataKey="week" stroke="var(--color-text-muted)" fontSize={11} />
                <YAxis domain={[0, 100]} unit="%" stroke="var(--color-text-muted)" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    background: 'var(--color-card-bg)',
                    borderColor: 'var(--color-card-border)',
                    color: 'var(--color-text-dark)',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="progress"
                  stroke={settings.accentColor}
                  fill={settings.accentColor}
                  fillOpacity={0.25}
                />
              </AreaChart>
            </ResponsiveContainer>
            <small className="text-[.62rem] text-[var(--color-text-muted)] block mt-2 text-right">
              * Progress trend based on sample cycle
            </small>
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
              Tracked study sessions and completed planner blocks. Azure Cosmos / Postgres analytics can later synchronize exact study timer logs.
            </p>
          </div>

          <SectionHeader icon="🎯" title="Activity Mix" />
          <div className="card p-5 flex items-center gap-4">
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
