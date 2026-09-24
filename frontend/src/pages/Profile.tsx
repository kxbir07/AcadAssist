import { useState, type FormEvent } from 'react';
import { Pencil, Save, Mail, MapPin, GraduationCap, Flame, Quote, BookOpen } from 'lucide-react';
import { useApp } from '../context/AppContext';
import Modal from '../components/ui/Modal';

export default function Profile() {
  const { user, updateUser, subjects, courses, pushToast } = useApp();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(user.fullName);
  const [role, setRole] = useState(user.role);
  const [field, setField] = useState(user.field);
  const [academicLevel, setAcademicLevel] = useState(user.academicLevel);
  const [bio, setBio] = useState(user.bio);
  const [quote, setQuote] = useState(user.quote);
  const [email, setEmail] = useState(user.email);
  const [location, setLocation] = useState(user.location);
  const enrolled = courses.filter(c => c.enrolled);

  const save = (e: FormEvent) => {
    e.preventDefault();
    updateUser({
      fullName: name.trim() || user.fullName,
      name: (name.trim() || user.fullName).split(' ')[0],
      role,
      field,
      academicLevel,
      bio,
      quote,
      email,
      location,
    });
    setEditing(false);
    pushToast('Profile saved');
  };

  return (
    <div className="page-stack">
      <div className="profile-hero card">
        <div className="profile-avatar-large">{user.name.slice(0, 1).toUpperCase()}</div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="eyebrow">MY PROFILE</span>
            <span className="soft-badge text-[.6rem]">{user.role} · Active Profile</span>
          </div>
          <h1>{user.fullName}</h1>
          <p>
            {user.role} · {user.academicLevel}
          </p>
          <div className="flex flex-wrap gap-2 mt-3">
            {user.tags.map(t => (
              <span className="soft-badge" key={t}>
                {t}
              </span>
            ))}
          </div>
        </div>
        <button className="btn primary" onClick={() => setEditing(true)}>
          <Pencil size={15} /> Edit profile
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_.8fr] gap-6">
        <div className="space-y-5">
          <div className="card p-5">
            <div className="section-title-row">
              <h2>About</h2>
              <Quote size={18} />
            </div>
            <p className="profile-bio">{user.bio || 'Add a short bio from Edit profile.'}</p>
            <div className="profile-info-grid">
              <div>
                <Mail size={15} />
                <span>{user.email}</span>
              </div>
              <div>
                <MapPin size={15} />
                <span>{user.location || 'Location not set'}</span>
              </div>
              <div>
                <GraduationCap size={15} />
                <span>{user.field}</span>
              </div>
              <div>
                <BookOpen size={15} />
                <span>Member since {user.memberSince}</span>
              </div>
            </div>
            <blockquote>“{user.quote}”</blockquote>
          </div>

          <div className="card p-5">
            <div className="section-title-row">
              <div>
                <div className="section-kicker">MY ENROLLED SUBJECTS</div>
                <h2>Current Coursework</h2>
              </div>
              <span className="soft-badge">{enrolled.length} active</span>
            </div>
            {subjects
              .filter(s => enrolled.some(c => c.name === s.name))
              .map(s => (
                <div className="profile-subject" key={s.id}>
                  <div className="flex-1">
                    <b>{s.name}</b>
                    <small>
                      {s.topicsCompleted}/{s.totalTopics} topics completed
                    </small>
                  </div>
                  <strong>{s.progress}%</strong>
                  <div className="progress-track">
                    <span style={{ width: `${s.progress}%`, background: s.color }} />
                  </div>
                </div>
              ))}
            {!enrolled.length && (
              <div className="empty-inline">
                Add a course from Courses to see your current learning here.
              </div>
            )}
          </div>
        </div>

        <div className="space-y-5">
          <div className="card p-5">
            <div className="flex justify-between items-center mb-2">
              <span className="section-kicker">STUDY STATS</span>
              <span className="text-[.6rem] text-[var(--color-text-muted)]">Activity Metrics</span>
            </div>
            <div className="stats-mini-grid">
              <div>
                <Flame size={18} />
                <strong>{user.streakDays}</strong>
                <small>day streak</small>
              </div>
              <div>
                <GraduationCap size={18} />
                <strong>{user.cgpa}</strong>
                <small>target grade</small>
              </div>
              <div>
                <BookOpen size={18} />
                <strong>{enrolled.length}</strong>
                <small>active courses</small>
              </div>
              <div>
                <Pencil size={18} />
                <strong>{subjects.reduce((a, s) => a + s.topicsCompleted, 0)}</strong>
                <small>topics practiced</small>
              </div>
            </div>
          </div>

          <div className="card p-5">
            <div className="section-kicker">STUDY PRINCIPLE</div>
            <h2 className="mt-2 text-base font-bold">{user.quote}</h2>
            <p className="muted text-xs mt-3 leading-relaxed">
              Use Profile to customize your academic identity and study preferences. Coursework activity remains synchronized with Courses, Knowledge, Assessment, and Planner.
            </p>
          </div>
        </div>
      </div>

      <Modal open={editing} onClose={() => setEditing(false)} title="Edit profile" wide>
        <form onSubmit={save}>
          <div className="form-grid">
            <label>
              Full name
              <input className="input" value={name} onChange={e => setName(e.target.value)} />
            </label>
            <label>
              Role
              <input className="input" value={role} onChange={e => setRole(e.target.value)} />
            </label>
            <label>
              Field / Program
              <input className="input" value={field} onChange={e => setField(e.target.value)} />
            </label>
            <label>
              Academic Level
              <input className="input" value={academicLevel} onChange={e => setAcademicLevel(e.target.value)} />
            </label>
            <label>
              Email
              <input className="input" type="email" value={email} onChange={e => setEmail(e.target.value)} />
            </label>
            <label>
              Location
              <input className="input" value={location} onChange={e => setLocation(e.target.value)} />
            </label>
          </div>
          <label>
            Bio
            <textarea className="textarea" rows={4} value={bio} onChange={e => setBio(e.target.value)} />
          </label>
          <label>
            Study Motto / Quote
            <textarea className="textarea" rows={2} value={quote} onChange={e => setQuote(e.target.value)} />
          </label>
          <div className="modal-actions">
            <button type="button" className="btn secondary" onClick={() => setEditing(false)}>
              Cancel
            </button>
            <button type="submit" className="btn primary">
              <Save size={14} /> Save profile
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
