import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Check, Clock3, Plus, Sparkles, Trash2, Pencil, CalendarDays,
  Target
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import HeroHeader from '../components/ui/HeroHeader';
import Modal from '../components/ui/Modal';
import { useApp, type CalendarEvent } from '../context/AppContext';

const TYPES: CalendarEvent['type'][] = ['Task', 'Exam', 'Class', 'Assignment', 'Study Session', 'Personal Event'];
const iso = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

const monthDays = (year: number, month: number) => {
  const first = new Date(year, month, 1).getDay();
  const total = new Date(year, month + 1, 0).getDate();
  const cells: number[] = [];
  for (let i = 0; i < first; i++) cells.push(0);
  for (let d = 1; d <= total; d++) cells.push(d);
  while (cells.length % 7) cells.push(0);
  return cells;
};

export default function Planner() {
  const {
    plannerTasks, togglePlannerTask, events, addEvent, updateEvent, deleteEvent,
    pushToast, settings, weakTopics, upcomingExams
  } = useApp();
  const navigate = useNavigate();

  const today = new Date();
  const [cursor, setCursor] = useState(new Date(today.getFullYear(), today.getMonth(), 1));
  const [view, setView] = useState<'Day' | 'Week' | 'Month'>('Month');
  const [selectedDate, setSelectedDate] = useState(iso(today));

  const [taskOpen, setTaskOpen] = useState(false);
  const [editEvent, setEditEvent] = useState<CalendarEvent | null>(null);
  const [focusOpen, setFocusOpen] = useState(false);
  const [focusSeconds, setFocusSeconds] = useState(0);

  const [title, setTitle] = useState('');
  const [time, setTime] = useState('5:00 PM');
  const [type, setType] = useState<CalendarEvent['type']>('Task');
  const [subject, setSubject] = useState('');
  const [notes, setNotes] = useState('');

  const hadFocusRef = useRef(false);
  useEffect(() => {
    if (focusSeconds <= 0) {
      if (hadFocusRef.current) {
        hadFocusRef.current = false;
        pushToast('Focus session complete — great study streak!');
      }
      return;
    }
    hadFocusRef.current = true;
    const id = window.setInterval(() => setFocusSeconds(s => Math.max(0, s - 1)), 1000);
    return () => window.clearInterval(id);
  }, [focusSeconds, pushToast]);

  const month = cursor.toLocaleString('en-US', { month: 'long' });
  const year = cursor.getFullYear();
  const cells = monthDays(year, cursor.getMonth());

  const visibleEvents = useMemo(() => {
    if (view === 'Day') {
      return events.filter(e => e.date === selectedDate).sort((a, b) => (a.time || '').localeCompare(b.time || ''));
    }
    if (view === 'Month') {
      return events.filter(e => e.date.startsWith(`${year}-${String(cursor.getMonth() + 1).padStart(2, '0')}`));
    }
    const start = new Date(selectedDate + 'T00:00:00');
    const day = start.getDay();
    const weekStart = new Date(start);
    weekStart.setDate(start.getDate() - day);
    const week = new Set(
      Array.from({ length: 7 }, (_, i) => {
        const d = new Date(weekStart);
        d.setDate(weekStart.getDate() + i);
        return iso(d);
      })
    );
    return events.filter(e => week.has(e.date));
  }, [view, events, year, cursor, selectedDate]);

  const openAdd = (date = selectedDate) => {
    setSelectedDate(date);
    setEditEvent(null);
    setTitle('');
    setTime('5:00 PM');
    setType('Task');
    setSubject('');
    setNotes('');
    setTaskOpen(true);
  };

  const openEdit = (e: CalendarEvent) => {
    setEditEvent(e);
    setTitle(e.title);
    setTime(e.time || '');
    setType(e.type);
    setSubject(e.subject || '');
    setNotes(e.notes || '');
    setSelectedDate(e.date);
    setTaskOpen(true);
  };

  const save = () => {
    if (!title.trim()) {
      pushToast('Enter a title', 'error');
      return;
    }
    const patch = {
      date: selectedDate,
      title: title.trim(),
      time: time.trim() || undefined,
      type,
      subject: subject.trim() || undefined,
      notes: notes.trim() || undefined,
    };
    if (editEvent) {
      updateEvent(editEvent.id, patch);
      pushToast('Event updated');
    } else {
      addEvent({ id: crypto.randomUUID(), ...patch, completed: false });
      pushToast('Added to planner');
    }
    setTaskOpen(false);
  };

  const startFocus = (minutes: number) => {
    setFocusSeconds(minutes * 60);
    setFocusOpen(false);
    pushToast(`${minutes}-minute focus session started`);
  };

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

  const primaryWeak = weakTopics[0];

  const schedulePipelineTask = () => {
    const targetSubject = nextExam?.subject || primaryWeak?.subject || 'Academic Study';
    const taskTitle = primaryWeak ? `Revise ${primaryWeak.topic} (${targetSubject})` : `Study ${targetSubject}`;
    addEvent({
      id: crypto.randomUUID(),
      date: iso(new Date()),
      title: taskTitle,
      time: '4:00 PM',
      type: 'Study Session',
      subject: targetSubject,
      notes: primaryWeak
        ? `Targeted revision for ${primaryWeak.topic}. Diagnostic accuracy: ${primaryWeak.accuracyScore}%.`
        : `Scheduled focus study session for ${targetSubject}.`,
      completed: false,
    });
    pushToast('Recommended revision session added to schedule');
  };

  const formatted = focusSeconds
    ? `${String(Math.floor(focusSeconds / 60)).padStart(2, '0')}:${String(focusSeconds % 60).padStart(2, '0')}`
    : '00:00';

  return (
    <div className="page-stack">
      <HeroHeader
        tag="STUDY PLANNER"
        title={
          <>
            Plan Today. Progress <span className="accent">Tomorrow.</span>
          </>
        }
        subtitle="Turn upcoming exam deadlines and weak topics into high-impact daily study sessions."
      />

      {/* Exam → Weak Topic → Recommended Study Task Pipeline Banner */}
      <div className="card p-4 border-l-4 border-l-[var(--color-green-accent)]">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="section-kicker text-[var(--color-green-accent)]">REVISION PIPELINE</span>
            <span className="soft-badge text-[.6rem]">Curriculum Driven</span>
          </div>
          <span className="text-[.65rem] text-[var(--color-text-muted)] font-medium">Revision Intelligence</span>
        </div>

        {nextExam || primaryWeak ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-2">
              {/* Step 1: Exam */}
              <div className="p-3 rounded-xl bg-[var(--color-page-bg)] border border-[var(--color-card-border)]">
                <small className="text-[.62rem] text-orange-600 dark:text-orange-400 font-bold uppercase block">1. Target Exam</small>
                <b className="text-xs text-[var(--color-text-dark)] block mt-0.5">
                  {nextExam?.examName || 'No upcoming exam scheduled'}
                </b>
                <span className="text-[.65rem] text-[var(--color-text-muted)] block mt-0.5">
                  {nextExam ? `${nextExam.subject} · in ${nextExam.daysLeft} days (${nextExam.dateStr})` : 'Add an exam below to set target dates'}
                </span>
              </div>

              {/* Step 2: Weak Topic */}
              <div className="p-3 rounded-xl bg-[var(--color-page-bg)] border border-[var(--color-card-border)]">
                <small className="text-[.62rem] text-red-600 dark:text-red-400 font-bold uppercase block">2. Identified Weak Topic</small>
                <b className="text-xs text-[var(--color-text-dark)] block mt-0.5">
                  {primaryWeak?.topic || 'No weak topics detected yet'}
                </b>
                <span className="text-[.65rem] text-red-600 dark:text-red-400 font-bold block mt-0.5">
                  {primaryWeak ? `Diagnostic accuracy: ${primaryWeak.accuracyScore}%` : 'Complete quizzes to detect focus areas'}
                </span>
              </div>

              {/* Step 3: Recommended Task */}
              <div className="p-3 rounded-xl bg-[var(--color-page-bg)] border border-[var(--color-card-border)]">
                <small className="text-[.62rem] text-green-700 dark:text-green-400 font-bold uppercase block">
                  3. Recommended Action
                </small>
                <b className="text-xs text-[var(--color-text-dark)] block mt-0.5">
                  {primaryWeak ? `45 min ${primaryWeak.topic} Review` : '45 min Scheduled Study Block'}
                </b>
                <span className="text-[.65rem] text-[var(--color-text-muted)] block mt-0.5">
                  {primaryWeak ? primaryWeak.recommendedAction : 'Solve practice questions and revise course notes'}
                </span>
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-3 pt-2 border-t border-[var(--color-border-light)]">
              {primaryWeak && (
                <button
                  className="btn secondary text-xs"
                  onClick={() =>
                    navigate(
                      `/assessment?topic=${encodeURIComponent(primaryWeak.topic.split(' ')[0])}`
                    )
                  }
                >
                  <Target size={14} /> Practice questions
                </button>
              )}
              <button className="btn primary text-xs" onClick={schedulePipelineTask}>
                <Plus size={14} /> Schedule recommended study session
              </button>
            </div>
          </>
        ) : (
          <div className="p-4 text-center text-xs text-[var(--color-text-muted)] flex flex-col items-center gap-2">
            <span>Schedule an exam or take an assessment quiz to automatically generate target revision tasks tailored to your weak areas.</span>
            <div className="flex gap-2 mt-1">
              <button className="btn secondary text-xs" onClick={() => openAdd()}>
                <Plus size={13} /> Add exam to calendar
              </button>
              <button className="btn primary text-xs" onClick={() => navigate('/assessment')}>
                <Target size={13} /> Take practice quiz
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Planner Toolbar */}
      <div className="planner-toolbar">
        <div className="flex items-center gap-2">
          <button
            className="icon-button"
            onClick={() => setCursor(new Date(year, cursor.getMonth() - 1, 1))}
            aria-label="Previous month"
          >
            ‹
          </button>
          <button
            className="btn subtle"
            onClick={() => {
              setCursor(new Date(today.getFullYear(), today.getMonth(), 1));
              setSelectedDate(iso(today));
            }}
          >
            Today
          </button>
          <button
            className="icon-button"
            onClick={() => setCursor(new Date(year, cursor.getMonth() + 1, 1))}
            aria-label="Next month"
          >
            ›
          </button>
          <h2 className="text-lg font-bold ml-2">
            {month} {year}
          </h2>
        </div>
        <div className="flex gap-2">
          <div className="view-switch">
            {(['Day', 'Week', 'Month'] as const).map(v => (
              <button key={v} onClick={() => setView(v)} className={view === v ? 'active' : ''}>
                {v}
              </button>
            ))}
          </div>
          <button className="btn primary" onClick={() => openAdd()}>
            <Plus size={15} /> Add event
          </button>
        </div>
      </div>

      {/* Three Column Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-[300px_1fr_300px] gap-6">
        {/* Left Column: Calendar + Today's Study Tasks */}
        <div>
          <div className="card calendar-card">
            <div className="calendar-head">
              <button
                className="icon-button"
                onClick={() => setCursor(new Date(year, cursor.getMonth() - 1, 1))}
              >
                ‹
              </button>
              <strong>
                {month} {year}
              </strong>
              <button
                className="icon-button"
                onClick={() => setCursor(new Date(year, cursor.getMonth() + 1, 1))}
              >
                ›
              </button>
            </div>
            <div className="calendar-week">
              {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((d, i) => (
                <span key={i}>{d}</span>
              ))}
            </div>
            <div className="calendar-days">
              {cells.map((d, i) =>
                d ? (
                  <button
                    key={i}
                    className={`${
                      selectedDate ===
                      `${year}-${String(cursor.getMonth() + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
                        ? 'selected '
                        : ''
                    }${
                      events.some(
                        e =>
                          e.date ===
                          `${year}-${String(cursor.getMonth() + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
                      )
                        ? 'has-event '
                        : ''
                    }`}
                    onClick={() =>
                      setSelectedDate(
                        `${year}-${String(cursor.getMonth() + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
                      )
                    }
                  >
                    {d}
                  </button>
                ) : (
                  <span key={i} />
                )
              )}
            </div>
          </div>

          <div className="card p-4 mt-4">
            <div className="section-title-row">
              <h3>Today's Tasks</h3>
              <span className="soft-badge">
                {plannerTasks.filter(t => t.completed).length}/{plannerTasks.length}
              </span>
            </div>
            {plannerTasks.length === 0 ? (
              <div className="p-4 text-center text-xs text-[var(--color-text-muted)] flex flex-col items-center gap-1.5">
                <span className="text-xl">📅</span>
                <b className="text-[var(--color-text-dark)]">Your study plan is empty.</b>
                <span>Create a study task to get started.</span>
                <button className="btn secondary text-xs mt-1" onClick={() => openAdd(iso(today))}>
                  <Plus size={13} /> Add Task
                </button>
              </div>
            ) : (
              <div className="space-y-1 mt-2">
                {plannerTasks.slice(0, 6).map(t => (
                  <div className="focus-item" key={t.id}>
                    <button
                      className={`check ${t.completed ? 'done' : ''}`}
                      onClick={() => togglePlannerTask(t.id)}
                      aria-label="Toggle task"
                    >
                      {t.completed && <Check size={13} />}
                    </button>
                    <div>
                      <b className={t.completed ? 'line-through opacity-50' : ''}>{t.title}</b>
                      <small>
                        {t.time} · {t.duration}
                      </small>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Center Column: Main Schedule View */}
        <div>
          <div className="card p-5">
            <div className="section-title-row">
              <div>
                <div className="section-kicker">{view.toUpperCase()} VIEW</div>
                <h2>
                  {view === 'Day'
                    ? selectedDate
                    : view === 'Week'
                    ? `Week containing ${selectedDate}`
                    : `${month} schedule`}
                </h2>
              </div>
              <button className="btn secondary text-xs" onClick={() => openAdd()}>
                <Plus size={14} /> Add schedule item
              </button>
            </div>
            <div className="event-list mt-5">
              {visibleEvents.length ? (
                visibleEvents.map(e => {
                  const isOverdue = !e.completed && e.date < iso(today);
                  const isToday = !e.completed && e.date === iso(today);
                  return (
                    <div
                      className={`event-row ${e.completed ? 'completed-row' : isOverdue ? 'overdue-row' : isToday ? 'today-row' : ''}`}
                      key={e.id}
                    >
                      <div className="event-time">{e.time || 'All day'}</div>
                      <div className={`event-dot ${e.type.toLowerCase().replaceAll(' ', '-')}`} />
                      <button className="event-content text-left" onClick={() => openEdit(e)}>
                        <div className="flex items-center gap-2">
                          <b className={e.completed ? 'line-through opacity-50' : ''}>{e.title}</b>
                          {isOverdue && (
                            <span className="text-[0.62rem] font-bold text-red-600 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/40 px-1.5 py-0.2 rounded">
                              Overdue
                            </span>
                          )}
                          {isToday && (
                            <span className="text-[0.62rem] font-bold text-emerald-700 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/40 px-1.5 py-0.2 rounded">
                              Today
                            </span>
                          )}
                          {e.completed && (
                            <span className="text-[0.62rem] font-bold text-[var(--color-text-muted)] bg-black/5 dark:bg-white/10 px-1.5 py-0.2 rounded">
                              Done
                            </span>
                          )}
                        </div>
                        <small>
                          {e.type}
                          {e.subject ? ` · ${e.subject}` : ''}
                          {e.notes ? ` · ${e.notes}` : ''}
                        </small>
                      </button>
                      <button
                        className="icon-button"
                        onClick={() => updateEvent(e.id, { completed: !e.completed })}
                        aria-label={e.completed ? 'Mark incomplete' : 'Mark complete'}
                      >
                        {e.completed ? <Check size={15} /> : <span>○</span>}
                      </button>
                      <button
                        className="icon-button danger"
                        onClick={() => deleteEvent(e.id)}
                        aria-label="Delete event"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  );
                })
              ) : (
                <div className="empty-state">
                  <CalendarDays size={28} />
                  <h3>No events scheduled</h3>
                  <p>Keep yourself on track by scheduling study blocks ahead of exams.</p>
                  <button className="btn primary mt-3" onClick={() => openAdd()}>
                    <Plus size={14} /> Add first event
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Focus Timer & Planning Tips */}
        <div>
          <div className="card p-4">
            <div className="section-title-row">
              <div>
                <h3>Focus Mode</h3>
                <p className="muted text-xs">Default: {settings.defaultStudyDuration} minutes</p>
              </div>
              <Clock3 size={18} />
            </div>
            {focusSeconds > 0 ? (
              <>
                <div className="focus-timer">{formatted}</div>
                <button className="btn secondary w-full" onClick={() => setFocusSeconds(0)}>
                  Stop session
                </button>
              </>
            ) : (
              <button className="btn primary w-full mt-4" onClick={() => setFocusOpen(true)}>
                <Sparkles size={15} /> Start focus session
              </button>
            )}
          </div>

          <div className="card p-4 mt-4">
            <div className="section-kicker">AI STUDY STRATEGY</div>
            <h3 className="mt-1">Prioritize what is closest to an exam.</h3>
            <p className="muted text-xs mt-2 leading-relaxed">
              {upcomingExams && upcomingExams.length > 0
                ? `${upcomingExams[0].title || upcomingExams[0].subjectId || 'Upcoming exam'} is in ${upcomingExams[0].daysUntilExam ?? 'a few'} days. Schedule 45-minute daily blocks to review key concepts.`
                : 'Review your course materials and practice key topics with 45-minute daily study blocks.'}
            </p>
            <button
              className="btn secondary w-full mt-3 text-xs"
              onClick={() => {
                setSelectedDate(iso(today));
                setView('Day');
                openAdd(iso(today));
              }}
            >
              Schedule next study block
            </button>
          </div>
        </div>
      </div>

      {/* Add / Edit Event Modal */}
      <Modal open={taskOpen} onClose={() => setTaskOpen(false)} title={editEvent ? 'Edit event' : 'Add to planner'}>
        <div className="form-grid">
          <label>
            Title
            <input className="input" value={title} onChange={e => setTitle(e.target.value)} />
          </label>
          <label>
            Date
            <input className="input" type="date" value={selectedDate} onChange={e => setSelectedDate(e.target.value)} />
          </label>
          <label>
            Time
            <input className="input" value={time} onChange={e => setTime(e.target.value)} placeholder="5:00 PM" />
          </label>
          <label>
            Type
            <select
              className="select full"
              value={type}
              onChange={e => setType(e.target.value as CalendarEvent['type'])}
            >
              {TYPES.map(t => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </label>
        </div>
        <label>
          Subject
          <input className="input" value={subject} onChange={e => setSubject(e.target.value)} />
        </label>
        <label>
          Notes
          <textarea className="textarea" rows={4} value={notes} onChange={e => setNotes(e.target.value)} />
        </label>
        <div className="modal-actions">
          <button className="btn secondary" onClick={() => setTaskOpen(false)}>
            Cancel
          </button>
          {editEvent && (
            <button
              className="btn danger"
              onClick={() => {
                deleteEvent(editEvent.id);
                setTaskOpen(false);
                pushToast('Event deleted', 'info');
              }}
            >
              <Trash2 size={14} /> Delete
            </button>
          )}
          <button className="btn primary" onClick={save}>
            <Pencil size={14} /> {editEvent ? 'Save changes' : 'Add event'}
          </button>
        </div>
      </Modal>

      {/* Focus Timer Preset Modal */}
      <Modal open={focusOpen} onClose={() => setFocusOpen(false)} title="Start a focused study session">
        <div className="grid grid-cols-3 gap-3">
          {[25, 50, 90].map(m => (
            <button key={m} className="card p-4 text-center hover:border-[var(--color-green-accent)]" onClick={() => startFocus(m)}>
              <Sparkles className="mx-auto mb-2" size={18} />
              <b>{m} min</b>
            </button>
          ))}
        </div>
        <button
          className="btn secondary w-full mt-3"
          onClick={() => {
            startFocus(settings.defaultStudyDuration);
          }}
        >
          Use my default ({settings.defaultStudyDuration} min)
        </button>
      </Modal>
    </div>
  );
}
