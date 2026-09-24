import type { ReactNode } from 'react';
import { Sparkles } from 'lucide-react';

interface HeroHeaderProps { tag:string; title:ReactNode; subtitle:string; image?:string; imageAlt?:string; }

export default function HeroHeader({tag,title,subtitle,image,imageAlt}:HeroHeaderProps){
  const heroAssets:Record<string,string>={
    'DASHBOARD':'/assets/header_dashboard.png',
    'STUDY PLANNER':'/assets/header_planner.png',
    'AI STUDY ASSISTANT':'/assets/header_assistant.png',
    'YOUR PROGRESS':'/assets/header_progress.png',
    'SETTINGS':'/assets/header_settings.png',
    'HELP & SUPPORT':'/assets/header_help_support.png',
    'AI ASSESSMENT STUDIO':'/assets/header_assessment.png',
    'MY KNOWLEDGE':'/assets/header_knowledge.png',
    'PROFILE':'/assets/header_profile.png',
  };
  const resolvedImage=image||heroAssets[tag];
  return <div className="hero-header">
    <div className="hero-text"><div className="hero-tag">{tag}</div><h1 className="hero-title">{title}</h1><p className="hero-subtitle">{subtitle}</p></div>
    <div className="hero-image" style={resolvedImage ? {backgroundImage:`linear-gradient(135deg,rgba(13,23,18,.22),rgba(23,51,36,.55)),url("${resolvedImage}")`,backgroundSize:'cover',backgroundPosition:'center'} : undefined} role={resolvedImage ? 'img' : undefined} aria-label={resolvedImage ? imageAlt || tag : undefined}><div className="hero-orb"><Sparkles size={30}/></div><div className="hero-grid-lines"/></div>
  </div>;
}
