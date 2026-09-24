import { useState, type FormEvent } from 'react';
import { ArrowLeft, Check, Eye, EyeOff, LockKeyhole, Mail, UserRound } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function validEmail(value:string){return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);}
export default function Signup(){
 const {signUp}=useAuth(); const navigate=useNavigate();
 const [name,setName]=useState(''); const [email,setEmail]=useState(''); const [password,setPassword]=useState(''); const [confirm,setConfirm]=useState('');
 const [show,setShow]=useState(false); const [error,setError]=useState('');
 const checks=[['8+ characters',password.length>=8],['One uppercase letter',/[A-Z]/.test(password)],['One number',/\d/.test(password)]];
 const submit=async (e:FormEvent)=>{e.preventDefault();setError('');
   if(name.trim().length<2){setError('Enter your full name.');return;}
   if(!validEmail(email)){setError('Enter a valid email address.');return;}
   if(!checks.every(([,ok])=>ok)){setError('Choose a password that meets all requirements.');return;}
   if(password!==confirm){setError('Passwords do not match.');return;}
   try { await signUp(name,email,password); navigate(`/login?created=1&email=${encodeURIComponent(email.trim().toLowerCase())}`); }
   catch(err){setError(err instanceof Error?err.message:'Unable to create account.');}
 };
 return <div className="auth-page"><div className="auth-side signup-side"><Link to="/" className="landing-brand"><span>A</span><strong>AcadAssist</strong></Link><div><div className="eyebrow">BUILD YOUR WORKSPACE</div><h1>Your courses, notes and practice — connected.</h1><p>Create a local account and start with a focused academic workspace.</p><div className="signup-benefits"><span><Check size={14}/>Courses & knowledge in one place</span><span><Check size={14}/>Practice with generated assessments</span><span><Check size={14}/>Progress saved on this device</span></div></div></div>
 <div className="auth-panel"><Link to="/" className="auth-back"><ArrowLeft size={15}/>Back to home</Link><div className="auth-form-wrap"><div className="eyebrow">CREATE ACCOUNT</div><h2>Start with AcadAssist</h2><p className="muted">This version stores your account locally until backend authentication is connected.</p>
 <form onSubmit={submit} className="auth-form">{error&&<div className="auth-error" role="alert">{error}</div>}
 <label>Full name<span className="auth-input"><UserRound size={16}/><input value={name} onChange={e=>setName(e.target.value)} autoComplete="name" placeholder="Your name"/></span></label>
 <label>Email<span className="auth-input"><Mail size={16}/><input type="email" value={email} onChange={e=>setEmail(e.target.value)} autoComplete="email" placeholder="you@example.com"/></span></label>
 <label>Password<span className="auth-input"><LockKeyhole size={16}/><input type={show?'text':'password'} value={password} onChange={e=>setPassword(e.target.value)} autoComplete="new-password" placeholder="Create a password"/><button type="button" className="password-toggle" onClick={()=>setShow(v=>!v)} aria-label={show?'Hide password':'Show password'}>{show?<EyeOff size={16}/>:<Eye size={16}/>}</button></span></label>
 <div className="password-rules">{checks.map(([label,ok])=><span className={ok?'ok':''} key={String(label)}><Check size={12}/>{String(label)}</span>)}</div>
 <label>Confirm password<span className="auth-input"><LockKeyhole size={16}/><input type={show?'text':'password'} value={confirm} onChange={e=>setConfirm(e.target.value)} autoComplete="new-password" placeholder="Repeat your password"/></span></label>
 <label className="consent"><input type="checkbox" required/> <span>I agree to use this local learning workspace on this device.</span></label>
 <button className="btn primary large auth-submit" type="submit">Create account</button>
 </form><p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p></div></div></div>;
}
