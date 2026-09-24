import { ArrowRight, BookOpen, BrainCircuit, CalendarDays, FileText, LineChart, Sparkles, Upload, CheckCircle2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import hero from '../assets/hero.png';

const features = [
  { icon: BrainCircuit, title: 'AI Study Assistant', text: 'Ask questions and get explanations grounded in the material you are studying.' },
  { icon: BookOpen, title: 'Knowledge Base', text: 'Keep course notes, documents and summaries in one focused learning workspace.' },
  { icon: FileText, title: 'AI Assessments', text: 'Generate practice quizzes, navigate questions freely and review mistakes.' },
  { icon: CalendarDays, title: 'Smart Planner', text: 'Turn deadlines and study goals into a practical daily plan.' },
  { icon: LineChart, title: 'Progress Tracking', text: 'See what is moving, what needs attention and how your study is progressing.' },
  { icon: Sparkles, title: 'Course Management', text: 'Organize subjects and keep your academic workload visible at a glance.' },
];

export default function Landing() {
  return <div className="landing-page">
    <nav className="landing-nav">
      <Link to="/" className="landing-brand"><span>A</span><strong>AcadAssist</strong></Link>
      <div className="landing-nav-links"><a href="#features">Features</a><a href="#workflow">How it works</a><a href="#preview">Preview</a></div>
      <div className="landing-nav-actions"><Link to="/login" className="btn secondary">Log in</Link><Link to="/signup" className="btn primary">Get started <ArrowRight size={15}/></Link></div>
    </nav>

    <main>
      <section className="landing-hero">
        <div className="landing-hero-copy">
          <div className="eyebrow">AI-POWERED LEARNING WORKSPACE</div>
          <h1>AI-powered learning,<br/><em>built around your curriculum.</em></h1>
          <p>Learn from your own notes, documents and courses with an intelligent study assistant that helps you understand, practice and plan.</p>
          <div className="landing-cta"><Link to="/signup" className="btn primary large">Get started free <ArrowRight size={16}/></Link><a href="#preview" className="btn secondary large">Explore AcadAssist</a></div>
          <div className="landing-proof"><span><CheckCircle2 size={14}/>Local-first workspace</span><span><CheckCircle2 size={14}/>Built for students</span><span><CheckCircle2 size={14}/>Practice & progress together</span></div>
        </div>
        <div className="landing-hero-visual">
          <div className="hero-glow"/>
          <div className="landing-image-frame"><img src={hero} alt="AcadAssist learning workspace preview"/></div>
          <div className="floating-learning-card"><Sparkles size={15}/><div><b>Focus session</b><small>Keep your weakest topic moving.</small></div></div>
        </div>
      </section>

      <section id="features" className="landing-section">
        <div className="landing-section-heading"><div><div className="eyebrow">ONE CONNECTED WORKSPACE</div><h2>Everything around the way you learn.</h2></div><p>AcadAssist connects study material, practice, planning and progress instead of treating them as separate tools.</p></div>
        <div className="landing-feature-grid">{features.map(({icon:Icon,title,text})=><article className="landing-feature-card" key={title}><div className="landing-feature-icon"><Icon size={18}/></div><h3>{title}</h3><p>{text}</p></article>)}</div>
      </section>

      <section id="workflow" className="landing-section workflow-section">
        <div className="landing-section-heading centered"><div><div className="eyebrow">A SIMPLE LOOP</div><h2>Upload. Understand. Practice. Improve.</h2></div></div>
        <div className="workflow-grid">{[
          { icon: Upload, num:'01', title:'Upload', text:'Bring your course material into your knowledge base.' },
          { icon: BrainCircuit, num:'02', title:'Understand', text:'Ask focused questions and turn dense material into clearer explanations.' },
          { icon: FileText, num:'03', title:'Practice', text:'Create quizzes and move directly between questions while you study.' },
          { icon: LineChart, num:'04', title:'Improve', text:'Review mistakes and use progress signals to decide what to study next.' },
        ].map(({icon:Icon,num,title,text})=><div className="workflow-step" key={num}><span>{num}</span><Icon size={20}/><h3>{title}</h3><p>{text}</p></div>)}</div>
      </section>

      <section id="preview" className="landing-preview">
        <div className="preview-copy"><div className="eyebrow">DESIGNED FOR FOCUS</div><h2>A calmer interface for serious study.</h2><p>Keep your subjects, materials, assessments and planning in one consistent environment without losing the premium feel of a modern product.</p><Link to="/signup" className="btn primary">Build your workspace <ArrowRight size={15}/></Link></div>
        <div className="preview-window"><div className="preview-window-bar"><span/><span/><span/><b>AcadAssist</b></div><img src="/assets/header_dashboard.png" alt="AcadAssist dashboard preview"/></div>
      </section>

      <section className="landing-final-cta"><div><div className="eyebrow">START YOUR WORKSPACE</div><h2>Make your next study session count.</h2><p>Set up your AcadAssist workspace and bring your learning workflow together.</p></div><Link to="/signup" className="btn primary large">Create account <ArrowRight size={16}/></Link></section>
    </main>

    <footer className="landing-footer"><div><div className="landing-brand"><span>A</span><strong>AcadAssist</strong></div><p>Learn · Plan · Practice · Grow</p></div><div className="footer-links"><a href="#features">Features</a><a href="#workflow">How it works</a><Link to="/login">Login</Link><Link to="/signup">Signup</Link></div><small>© {new Date().getFullYear()} AcadAssist · Local-first frontend</small></footer>
  </div>;
}
