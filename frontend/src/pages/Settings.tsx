import { useState } from 'react';
import { Download, Shield, Lock, UserRound, Plus, Pencil, Trash2, Moon, Sun, Monitor, Check } from 'lucide-react';
import HeroHeader from '../components/ui/HeroHeader';
import SectionHeader from '../components/ui/SectionHeader';
import Modal from '../components/ui/Modal';
import { useApp } from '../context/AppContext';

export default function Settings() {
  const {
    settings, updateSetting, subjects, addSubject, updateSubject, deleteSubject,
    pushToast, chatHistory, notes, user, updateUser
  } = useApp();
  const [modal, setModal] = useState<string | null>(null);
  const [editing, setEditing] = useState<typeof subjects[number] | null>(null);
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [semester, setSemester] = useState('');
  const [examDate, setExamDate] = useState('');
  const [importance, setImportance] = useState<'Low' | 'Medium' | 'High'>('Medium');
  const [bio, setBio] = useState(user.bio);
  const [displayName, setDisplayName] = useState(user.fullName);

  const openSubject = (s?: typeof subjects[number]) => {
    setEditing(s || null);
    setName(s?.name || '');
    setCode(s?.code || s?.tag || '');
    setSemester(s?.semester || '');
    setExamDate(s?.examDate || '');
    setImportance(s?.importance || 'Medium');
    setModal('subject');
  };

  const saveSubject = () => {
    if (!name.trim()) {
      pushToast('Subject name is required', 'error');
      return;
    }
    const patch = {
      name: name.trim(),
      fullName: name.trim(),
      tag: code.trim() || 'CUSTOM',
      code: code.trim() || undefined,
      semester: semester.trim() || undefined,
      examDate: examDate || undefined,
      importance,
    };
    if (editing) {
      updateSubject(editing.id, patch);
      pushToast('Subject updated');
    } else {
      addSubject({
        id: crypto.randomUUID(),
        ...patch,
        documentsCount: 0,
        progress: 0,
        topicsCompleted: 0,
        totalTopics: 10,
        color: '#2d5f47',
      });
      pushToast('Subject added');
    }
    setModal(null);
  };

  const exportData = () => {
    const data = { user, settings, subjects, notes, chatHistory };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'acadassist-data.json';
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    pushToast('Your local data was exported');
  };

  return (
    <div className="page-stack">
      <HeroHeader
        tag="SETTINGS"
        title={
          <>
            Make AcadAssist <span className="accent">Yours.</span>
          </>
        }
        subtitle="Control study preferences, appearance, notifications, profile, and local storage data."
      />
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div>
          <SectionHeader icon="📚" title="Study Preferences" />
          <div className="card p-5 mb-6">
            <label>
              Default study duration
              <select
                className="select full"
                value={settings.defaultStudyDuration}
                onChange={e => updateSetting('defaultStudyDuration', Number(e.target.value))}
              >
                <option value={25}>25 minutes (Pomodoro)</option>
                <option value={50}>50 minutes (Deep Focus)</option>
                <option value={90}>90 minutes (Exam Simulation)</option>
              </select>
            </label>
            <label>
              Preferred difficulty
              <select
                className="select full"
                value={settings.preferredDifficulty}
                onChange={e => updateSetting('preferredDifficulty', e.target.value)}
              >
                {['Easy', 'Medium', 'Hard', 'Mixed'].map(x => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>

            <div className="flex items-center justify-between mt-5 mb-2">
              <b className="text-xs">My Enrolled Subjects</b>
              <button className="btn subtle" onClick={() => openSubject()}>
                <Plus size={14} /> Add subject
              </button>
            </div>
            {subjects.length ? (
              subjects.map(s => (
                <div key={s.id} className="flex items-center gap-2 py-3 border-b border-[var(--color-border-light)]">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: s.color }} />
                  <div className="flex-1 min-w-0">
                    <b className="text-xs truncate block">{s.name}</b>
                    <small className="block text-[.62rem] text-[var(--color-text-muted)]">
                      {s.code || s.tag} · {s.importance || 'Medium'} priority
                      {s.examDate ? ` · Exam ${s.examDate}` : ''}
                    </small>
                  </div>
                  <button className="icon-button" onClick={() => openSubject(s)} aria-label="Edit subject">
                    <Pencil size={13} />
                  </button>
                  <button
                    className="icon-button danger"
                    onClick={() => {
                      deleteSubject(s.id);
                      pushToast('Subject removed', 'info');
                    }}
                    aria-label="Remove subject"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))
            ) : (
              <div className="empty-inline">No subjects yet.</div>
            )}
          </div>

          <SectionHeader icon="🔔" title="Study Notifications" />
          <div className="card p-5 mb-6">
            {[
              ['dailyReminder', 'Daily Study Reminder'],
              ['assessmentFeedback', 'Assessment Diagnostic Feedback'],
              ['examAlerts', 'Upcoming Exam Alerts (5-day warning)'],
              ['progressReport', 'Weekly Curriculum Progress Report'],
              ['streakUpdates', 'Study Streak Milestone Alerts'],
              ['newFeatures', 'Azure Integration Sync Updates'],
            ].map(([key, label]) => (
              <div
                key={key}
                className="flex items-center py-3 border-b last:border-0 border-[var(--color-border-light)]"
              >
                <span className="flex-1 text-xs font-semibold">{label}</span>
                <button
                  role="switch"
                  aria-checked={!!settings[key as keyof typeof settings]}
                  onClick={() => updateSetting(key, !settings[key as keyof typeof settings])}
                  className={`toggle-switch ${settings[key as keyof typeof settings] ? 'active' : ''}`}
                >
                  <span />
                </button>
              </div>
            ))}
          </div>

          <SectionHeader icon="👤" title="Profile Details" />
          <div className="card p-5">
            <label>
              Display name
              <input className="input" value={displayName} onChange={e => setDisplayName(e.target.value)} />
            </label>
            <label>
              Bio / Goals
              <textarea className="textarea" rows={3} value={bio} onChange={e => setBio(e.target.value)} />
            </label>
            <button
              className="btn primary mt-3"
              onClick={() => {
                updateUser({
                  fullName: displayName.trim() || user.fullName,
                  name: (displayName.trim() || user.fullName).split(' ')[0],
                  bio,
                });
                pushToast('Profile updated');
              }}
            >
              <Check size={14} /> Save profile
            </button>
          </div>
        </div>

        <div>
          <SectionHeader icon="🎨" title="Appearance & Themes" />
          <div className="card p-5 mb-6">
            <b className="text-xs">Theme Mode</b>
            <div className="grid grid-cols-3 gap-2 my-3">
              {([['light', Sun], ['dark', Moon], ['system', Monitor]] as const).map(([t, Icon]) => (
                <button
                  key={t}
                  className={`btn ${settings.theme === t ? 'primary' : 'subtle'}`}
                  onClick={() => updateSetting('theme', t)}
                >
                  <Icon size={14} />
                  <span className="capitalize">{t}</span>
                </button>
              ))}
            </div>

            <b className="text-xs">Application Accent Color</b>
            <div className="flex gap-3 my-3">
              {['#2d5f47', '#6366f1', '#3b82f6', '#f59e0b', '#ef4444', '#ec4899'].map(c => (
                <button
                  key={c}
                  aria-label={`Use ${c}`}
                  className="w-7 h-7 rounded-full transition-transform hover:scale-110"
                  style={{
                    background: c,
                    outline: settings.accentColor === c ? '3px solid var(--color-text-dark)' : 'none',
                    outlineOffset: 2,
                  }}
                  onClick={() => {
                    updateSetting('accentColor', c);
                    pushToast('Accent color updated');
                  }}
                />
              ))}
            </div>

            <b className="text-xs">Base Font Size</b>
            <div className="grid grid-cols-3 gap-2 mt-3">
              {(['small', 'medium', 'large'] as const).map(s => (
                <button
                  key={s}
                  className={`btn ${settings.fontSize === s ? 'primary' : 'subtle'}`}
                  onClick={() => updateSetting('fontSize', s)}
                >
                  <span className="capitalize">{s}</span>
                </button>
              ))}
            </div>
          </div>

          <SectionHeader icon="🛡️" title="Security & Authentication" />
          <div className="card p-2 mb-6">
            {[
              ['Change Password', 'password'],
              ['Two-Factor Authentication', '2fa'],
              ['Active Sessions', 'sessions'],
            ].map(([label, key]) => (
              <button
                key={key}
                className="w-full flex justify-between py-3 px-3 text-left border-b last:border-0 border-[var(--color-border-light)] text-xs"
                onClick={() => setModal(key)}
              >
                <span>{label}</span>
                <span>›</span>
              </button>
            ))}
            <button
              className="w-full flex justify-between py-3 px-3 text-left text-xs text-red-600"
              onClick={() => setModal('delete')}
            >
              <span>Delete Account</span>
              <span>›</span>
            </button>
          </div>

          <SectionHeader icon="💾" title="Local Data & Exports" />
          <div className="card p-2">
            <button className="w-full flex justify-between py-3 px-3 text-left text-xs" onClick={exportData}>
              <span>Export local study workspace (JSON)</span>
              <Download size={14} />
            </button>
            <button
              className="w-full flex justify-between py-3 px-3 text-left border-t border-[var(--color-border-light)] text-xs"
              onClick={() => setModal('clear')}
            >
              <span>Clear local AI conversation history</span>
              <Trash2 size={14} />
            </button>
          </div>
        </div>
      </div>

      <Modal open={modal === 'subject'} onClose={() => setModal(null)} title={editing ? 'Edit subject' : 'Add subject'}>
        <label>
          Subject name
          <input className="input" value={name} onChange={e => setName(e.target.value)} />
        </label>
        <div className="form-grid">
          <label>
            Code
            <input className="input" value={code} onChange={e => setCode(e.target.value)} />
          </label>
          <label>
            Semester
            <input className="input" value={semester} onChange={e => setSemester(e.target.value)} />
          </label>
          <label>
            Exam date
            <input className="input" type="date" value={examDate} onChange={e => setExamDate(e.target.value)} />
          </label>
          <label>
            Importance
            <select
              className="select full"
              value={importance}
              onChange={e => setImportance(e.target.value as typeof importance)}
            >
              <option>Low</option>
              <option>Medium</option>
              <option>High</option>
            </select>
          </label>
        </div>
        <div className="modal-actions">
          <button className="btn secondary" onClick={() => setModal(null)}>
            Cancel
          </button>
          <button className="btn primary" onClick={saveSubject}>
            {editing ? 'Save changes' : 'Create subject'}
          </button>
        </div>
      </Modal>

      <Modal
        open={modal === 'password' || modal === '2fa' || modal === 'sessions'}
        onClose={() => setModal(null)}
        title={
          modal === 'password'
            ? 'Change Password'
            : modal === '2fa'
            ? 'Two-Factor Authentication'
            : 'Manage Sessions'
        }
      >
        <p className="text-sm">
          Authentication and security settings will connect to your production identity provider (e.g. Azure Entra ID / Supabase). The frontend is integration-ready and does not simulate credentials locally.
        </p>
        <div className="modal-actions">
          <button
            className="btn primary"
            onClick={() => {
              setModal(null);
              pushToast('Backend identity provider required for auth management', 'info');
            }}
          >
            {modal === '2fa' ? <Shield size={14} /> : modal === 'password' ? <Lock size={14} /> : <UserRound size={14} />}
            Understood
          </button>
        </div>
      </Modal>

      <Modal open={modal === 'clear'} onClose={() => setModal(null)} title="Clear AI conversation">
        <p className="text-sm">
          This will clear the locally saved conversation messages with AcadAssist AI. Your uploaded documents and notes will remain intact.
        </p>
        <div className="modal-actions">
          <button className="btn secondary" onClick={() => setModal(null)}>
            Cancel
          </button>
          <button
            className="btn danger"
            onClick={() => {
              localStorage.removeItem('acadassist.chat');
              window.location.reload();
            }}
          >
            Clear conversation
          </button>
        </div>
      </Modal>

      <Modal open={modal === 'delete'} onClose={() => setModal(null)} title="Delete account">
        <p className="text-sm">
          Account deletion requires verification by your connected backend. No mock deletion is performed locally.
        </p>
        <div className="modal-actions">
          <button className="btn secondary" onClick={() => setModal(null)}>
            Cancel
          </button>
          <button
            className="btn danger"
            onClick={() => {
              setModal(null);
              pushToast('Account deletion API required', 'error');
            }}
          >
            Understood
          </button>
        </div>
      </Modal>
    </div>
  );
}
