import { useMemo, useState } from 'react';
import { BookOpen, Check, Clock3, Plus, Search, Sparkles, Trophy } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { calculateCourseProgress } from '../utils/courseProgress';

export default function Courses(){
 const {courses,addCourse,removeCourse,pushToast,subjects,addSubject,deleteSubject,courseProgress,coursePreferences}=useApp();
 const navigate=useNavigate(); const [q,setQ]=useState(''); const [category,setCategory]=useState('All'); const [enrolledOnly,setEnrolledOnly]=useState(false);
 const categories=useMemo(()=>['All',...Array.from(new Set(courses.map(c=>c.category).filter(Boolean))).sort()],[courses]);
 const preferenceScoped=useMemo(()=>{
   const sorted=[...courses].sort((a,b)=>a.id.localeCompare(b.id));
   if(!coursePreferences.length) return sorted.slice(0,20);
   return sorted.filter(c=>coursePreferences.includes(c.specialization || c.category));
 },[courses,coursePreferences]);
 const filtered=useMemo(()=>preferenceScoped.filter(c=>{
   const matchCategory=category==='All'||c.category===category;
   const matchSearch=`${c.name} ${c.code} ${c.category} ${c.specialization||''}`.toLowerCase().includes(q.toLowerCase());
   const matchEnrolled=!enrolledOnly||c.enrolled;
   return matchCategory&&matchSearch&&matchEnrolled;
 }),[preferenceScoped,q,category,enrolledOnly]);

 const enroll=(id:string)=>{
   addCourse(id); const c=courses.find(x=>x.id===id);
   if(c && !subjects.some(s=>s.id===c.id || (s.name===c.name && s.tag===c.code))){
     addSubject({id:c.id,name:c.name,fullName:c.name,documentsCount:0,progress:0,topicsCompleted:0,totalTopics:c.lessonCount || c.topics.length,color:c.color,tag:c.code});
   }
   if(c) pushToast(`${c.name} added to My Subjects`,'success');
 };
 const unenroll=(c:{id:string,name:string})=>{
   removeCourse(c.id);
   const linked=subjects.find(s=>s.id===c.id);
   if(linked) deleteSubject(linked.id);
   pushToast('Course removed from My Subjects','info');
 };
 const progress=(c:typeof courses[number])=>calculateCourseProgress(c, courseProgress[c.id]).overallPct;

 return <div className="page-stack">
  <div className="page-hero">
   <div><div className="eyebrow">COURSE LIBRARY · {coursePreferences.length ? `${preferenceScoped.length} MATCHING COURSES` : `20 GENERAL COURSES`}</div><h1>Learn something new.</h1><p>{coursePreferences.length ? `Showing courses from your selected learning fields: ${coursePreferences.join(', ')}.` : 'No learning fields selected — showing 20 deterministic general courses. Change this anytime from Profile.'}</p></div>
   <button className="btn primary" onClick={()=>navigate('/knowledge')}><Sparkles size={16}/>Build from my material</button>
  </div>
  <div className="toolbar">
   <div className="search-box"><Search size={17}/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search courses, subjects, specializations..."/></div>
   <div className="chip-row">{categories.map(c=><button key={c} className={`filter-chip ${category===c?'active':''}`} onClick={()=>setCategory(c)}>{c}</button>)}<button className={`filter-chip ${enrolledOnly?'active':''}`} onClick={()=>setEnrolledOnly(x=>!x)}>My Courses</button></div>
  </div>
  <div className="course-grid">
   {filtered.map(c=>{const pct=progress(c); return <div className="course-card" key={c.id}>
    <div className="course-accent" style={{background:c.color}}/><div className="course-card-body">
     <div className="course-icon" style={{background:`${c.color}18`,color:c.color}}><BookOpen size={20}/></div>
     <div className="course-meta"><span>{c.code}</span><span>{c.specialization || c.category}</span></div>
     <h3>{c.name}</h3><p>{c.description}</p>
     <div className="topic-row">{c.topics.slice(0,3).map(t=><span key={t}>{t}</span>)}{(c.lessonCount||c.topics.length)>3&&<span>+{(c.lessonCount||c.topics.length)-3} lessons</span>}</div>
     <div className="course-footer"><span><Clock3 size={14}/>{c.estimatedHours}h</span><span>{pct}% progress</span></div>
     <div className="progress-track"><span style={{width:`${pct}%`,background:c.color}}/></div>
     <div className="course-actions">
       <button className="btn secondary" onClick={()=>navigate(`/courses/${c.id}`)}>View course</button>
       <button className="btn subtle" onClick={()=>navigate(`/courses/${c.id}/quiz`)}><Trophy size={15}/>Quiz</button>
       {c.enrolled ? <button className="btn subtle" onClick={()=>unenroll(c)}><Check size={15}/>Added</button> :
         <button className="btn primary" onClick={()=>enroll(c.id)}><Plus size={15}/>Add</button>}
     </div>
    </div>
   </div>})}
  </div>
  {!filtered.length&&<div className="empty-state"><BookOpen size={30}/><h3>No courses found</h3><p>Try another search, category or remove the My Courses filter.</p></div>}
 </div>
}
