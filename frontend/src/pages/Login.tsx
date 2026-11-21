import { useState, type FormEvent } from 'react';
import { ArrowLeft, CheckCircle2, Eye, EyeOff, KeyRound, LockKeyhole, Mail } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useApp } from '../context/AppContext';
import { requestPasswordReset, confirmPasswordReset } from '../services/auth';
import Modal from '../components/ui/Modal';

export default function Login() {
  const { signIn } = useAuth();
  const { updateUser, pushToast } = useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const next = searchParams.get('next') || '/dashboard';
  const createdBanner = searchParams.get('created') === '1';
  const initialEmail = searchParams.get('email') || '';

  const [email, setEmail] = useState(initialEmail);
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Forgot / Reset password state
  const [resetOpen, setResetOpen] = useState(false);
  const [resetEmail, setResetEmail] = useState(initialEmail);
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [resetStep, setResetStep] = useState<'request' | 'confirm'>('request');
  const [resetError, setResetError] = useState('');
  const [resetInfo, setResetInfo] = useState('');
  const [resetBusy, setResetBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email.trim() || !password) {
      setError('Enter your email and password.');
      return;
    }
    setSubmitting(true);
    try {
      const account = await signIn(email, password);
      updateUser({
        name: account.name.split(' ')[0] || account.name,
        fullName: account.name,
        email: account.email,
        role: account.role || 'Student',
        field: account.fieldOfStudy || 'Computer Science',
        academicLevel: account.academicLevel || 'Undergraduate',
        bio: account.bio || 'AcadAssist Scholar',
      });
      navigate(next, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to sign in.');
    } finally {
      setSubmitting(false);
    }
  };

  const openForgotModal = () => {
    setResetEmail(email.trim() || '');
    setResetToken('');
    setNewPassword('');
    setConfirmNewPassword('');
    setResetStep('request');
    setResetError('');
    setResetInfo('');
    setResetOpen(true);
  };

  const handleRequestReset = async (e: FormEvent) => {
    e.preventDefault();
    setResetError('');
    setResetInfo('');
    if (!resetEmail.trim()) {
      setResetError('Please enter your account email address.');
      return;
    }
    setResetBusy(true);
    try {
      const res = await requestPasswordReset(resetEmail);
      setResetInfo(res.message);
      if (res.resetToken) {
        setResetToken(res.resetToken);
      }
      setResetStep('confirm');
    } catch (err) {
      setResetError(err instanceof Error ? err.message : 'Unable to request password reset.');
    } finally {
      setResetBusy(false);
    }
  };

  const handleConfirmReset = async (e: FormEvent) => {
    e.preventDefault();
    setResetError('');
    if (!resetToken.trim()) {
      setResetError('Enter the verification reset token.');
      return;
    }
    if (newPassword.length < 8) {
      setResetError('New password must be at least 8 characters long.');
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setResetError('New passwords do not match.');
      return;
    }
    setResetBusy(true);
    try {
      const msg = await confirmPasswordReset(resetToken, newPassword);
      setEmail(resetEmail.trim().toLowerCase());
      setPassword('');
      setResetOpen(false);
      pushToast(msg, 'success');
    } catch (err) {
      setResetError(err instanceof Error ? err.message : 'Unable to reset password.');
    } finally {
      setResetBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-side">
        <Link to="/" className="landing-brand">
          <span>A</span>
          <strong>AcadAssist</strong>
        </Link>
        <div>
          <div className="eyebrow">YOUR LEARNING WORKSPACE</div>
          <h1>Return to a study system that keeps everything connected.</h1>
          <p>Pick up your courses, knowledge, assessments and plans from one place.</p>
        </div>
        <div className="auth-side-note">
          “Small sessions.
          <br />
          Compounding progress.”
        </div>
      </div>

      <div className="auth-panel">
        <Link to="/" className="auth-back">
          <ArrowLeft size={15} />
          Back to home
        </Link>
        <div className="auth-form-wrap">
          <div className="eyebrow">WELCOME BACK</div>
          <h2>Sign in to AcadAssist</h2>
          <p className="muted">Enter your registered email and password to access your workspace.</p>

          {createdBanner && (
            <div className="p-3 mb-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2">
              <CheckCircle2 size={15} />
              <span>Account created! Sign in below to enter your workspace.</span>
            </div>
          )}

          <form onSubmit={submit} className="auth-form">
            {error && (
              <div className="auth-error" role="alert">
                {error}
              </div>
            )}
            <label>
              Email
              <span className="auth-input">
                <Mail size={16} />
                <input
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                />
              </span>
            </label>
            <label>
              Password
              <span className="auth-input">
                <LockKeyhole size={16} />
                <input
                  type={show ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShow(v => !v)}
                  aria-label={show ? 'Hide password' : 'Show password'}
                >
                  {show ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </span>
            </label>
            <div className="auth-options">
              <span className="auth-local-badge">JWT Protected</span>
              <button type="button" className="text-action" onClick={openForgotModal}>
                Forgot password?
              </button>
            </div>
            <button className="btn primary large auth-submit" type="submit" disabled={submitting}>
              {submitting ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
          <p className="auth-switch">
            New to AcadAssist? <Link to="/signup">Create an account</Link>
          </p>
          <small className="auth-footnote">
            Authenticated sessions use bcrypt password hashing and signed Bearer JWT tokens.
          </small>
        </div>
      </div>

      {/* Password Recovery Modal */}
      <Modal
        open={resetOpen}
        onClose={() => !resetBusy && setResetOpen(false)}
        title="Password Recovery"
        subtitle={
          resetStep === 'request'
            ? 'Enter your account email to generate a secure password reset token.'
            : 'Verify your reset token and set a new password.'
        }
      >
        {resetError && (
          <div className="auth-error mb-3" role="alert">
            {resetError}
          </div>
        )}
        {resetInfo && (
          <div className="p-3 mb-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800">
            {resetInfo}
          </div>
        )}

        {resetStep === 'request' ? (
          <form onSubmit={handleRequestReset}>
            <label>
              Registered Email
              <input
                className="input"
                type="email"
                value={resetEmail}
                onChange={e => setResetEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </label>
            <div className="modal-actions mt-4">
              <button type="button" className="btn secondary" onClick={() => setResetOpen(false)}>
                Cancel
              </button>
              <button type="submit" className="btn primary" disabled={resetBusy}>
                <KeyRound size={14} /> {resetBusy ? 'Generating token…' : 'Send Reset Token'}
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleConfirmReset}>
            <label>
              Verification Reset Token
              <input
                className="input font-mono text-xs"
                value={resetToken}
                onChange={e => setResetToken(e.target.value)}
                placeholder="Paste your signed reset token"
                required
              />
            </label>
            <label>
              New Password (min 8 characters)
              <input
                className="input"
                type="password"
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                placeholder="Create a new password"
                required
              />
            </label>
            <label>
              Confirm New Password
              <input
                className="input"
                type="password"
                value={confirmNewPassword}
                onChange={e => setConfirmNewPassword(e.target.value)}
                placeholder="Repeat new password"
                required
              />
            </label>
            <div className="modal-actions mt-4">
              <button
                type="button"
                className="btn secondary"
                onClick={() => setResetStep('request')}
                disabled={resetBusy}
              >
                Back
              </button>
              <button type="submit" className="btn primary" disabled={resetBusy}>
                <CheckCircle2 size={14} /> {resetBusy ? 'Resetting…' : 'Reset Password'}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
