import { useState, type FormEvent } from 'react';
import { ArrowLeft, Eye, EyeOff, LockKeyhole, Mail } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useApp } from '../context/AppContext';

export default function Login() {
  const { signIn } = useAuth();
  const { updateUser } = useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const next = new URLSearchParams(location.search).get('next') || '/dashboard';
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  const [show,setShow]=useState(false);
  const [error,setError]=useState('');

  const submit=async (e:FormEvent)=>{
    e.preventDefault(); setError('');
    if(!email.trim() || !password){setError('Enter your email and password.');return;}
    try {
      const account=await signIn(email,password);
      updateUser({name:account.name,email:account.email});
      navigate(next,{replace:true});
    } catch(err) { setError(err instanceof Error?err.message:'Unable to sign in.'); }
  };


  return <div className="auth-page"><div className="auth-side"><Link to="/" className="landing-brand"><span>A</span><strong>AcadAssist</strong></Link><div><div className="eyebrow">YOUR LEARNING WORKSPACE</div><h1>Return to a study system that keeps everything connected.</h1><p>Pick up your courses, knowledge, assessments and plans from one place.</p></div><div className="auth-side-note">“Small sessions.<br/>Compounding progress.”</div></div>
    <div className="auth-panel"><Link to="/" className="auth-back"><ArrowLeft size={15}/>Back to home</Link><div className="auth-form-wrap"><div className="eyebrow">WELCOME BACK</div><h2>Sign in to AcadAssist</h2><p className="muted">Use the local account you created on this device.</p>
      <form onSubmit={submit} className="auth-form">
        {error&&<div className="auth-error" role="alert">{error}</div>}
        <label>Email<span className="auth-input"><Mail size={16}/><input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com"/></span></label>
        <label>Password<span className="auth-input"><LockKeyhole size={16}/><input type={show?'text':'password'} autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Enter your password"/><button type="button" className="password-toggle" onClick={()=>setShow(v=>!v)} aria-label={show?'Hide password':'Show password'}>{show?<EyeOff size={16}/>:<Eye size={16}/>}</button></span></label>
        <div className="auth-options"><span className="auth-local-badge">Local account</span><button type="button" className="text-action" onClick={()=>setError('Password recovery is not connected yet. Your local account stays on this device.')}>Forgot password?</button></div>
        <button className="btn primary large auth-submit" type="submit">Sign in</button>
      </form>
      <p className="auth-switch">New to AcadAssist? <Link to="/signup">Create an account</Link></p>
      <small className="auth-footnote">Local authentication is intentionally isolated behind an auth service so a real backend can replace it later.</small>
    </div></div>
  </div>;
}
