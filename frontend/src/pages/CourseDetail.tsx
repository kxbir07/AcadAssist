import { useEffect, useState } from 'react';
import { ArrowLeft, CheckCircle2, Circle, ChevronDown, ChevronRight, Clock3, PlayCircle, Trophy } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { useApp, type Course, type CourseModule } from '../context/AppContext';
import { calculateCourseProgress, calculateModuleProgress } from '../utils/courseProgress';

function normalizeCourse(c:Course):Course {
  if (c.modules?.length) return c;
  const modules:CourseModule[]=(c.topics || []).map((topic,i)=>({
    id:`${c.id}-m${i+1}`, number:i+1, title:topic, coverage:`Study the core concepts, mechanisms, examples and applications of ${topic}.`,
    content:`Study the core concepts, mechanisms, examples and applications of ${topic}.`,
    lessons:[{id:`${c.id}-m${i+1}-l1`,title:topic,description:`Structured lesson covering the core concepts, mechanisms, examples and applications of ${topic}.`,content:`Study the core concepts, mechanisms, examples and applications of ${topic}.`}]
  }));
  return {...c,modules};
}

export default function CourseDetail(){
 const {courseId}=useParams(); const navigate=useNavigate();
 const {courses,courseProgress,markCourseLesson,setLastCourseLesson,addCourse,pushToast}=useApp();
 const base=courses.find(c=>c.id===courseId);
 const [course,setCourse]=useState<Course|undefined>(base ? normalizeCourse(base):undefined);
 const [open,setOpen]=useState<string|null>(null);

 useEffect(()=>{ if(!courseId)return; let cancelled=false;
   fetch(`/data/courses/${encodeURIComponent(courseId)}.json`).then(r=>r.ok?r.json():Promise.reject()).then((data:Course)=>{if(!cancelled)setCourse(data)}).catch(()=>{ if(!cancelled&&base)setCourse(normalizeCourse(base)); });
   return ()=>{cancelled=true};
 },[courseId,base]);

 const modules=course?.modules || [];
 const progress=courseId ? (courseProgress[courseId] || {completedLessonIds:[],completedQuizIds:[]}) : {completedLessonIds:[],completedQuizIds:[]};
 const completed=new Set(progress.completedLessonIds || []);
 const completedQuizIds=new Set(progress.completedQuizIds || []);
 const moduleQuizzes=course?.moduleQuizzes || [];
 const finalQuiz=course?.finalQuiz || course?.quiz;
 const summary=course ? calculateCourseProgress(course, progress) : {totalLessons:0,completedLessons:0,learningPct:0,totalQuizzes:0,completedQuizzes:0,assessmentPct:0,overallPct:0,completed:false,lessonRemaining:0};
 const learningPct=summary.learningPct;
 const assessmentPct=summary.assessmentPct;
 const percent=summary.overallPct;
 const courseComplete=summary.completed;
 const lastId=courseId ? courseProgress[courseId]?.lastLessonId : undefined;
 const nextLesson=modules.flatMap(m=>m.lessons).find(l=>!completed.has(l.id)) || modules[0]?.lessons[0];

 if(!course) return <div className="page-stack"><div className="empty-state"><h3>Course not found</h3><button className="btn secondary" onClick={()=>navigate('/courses')}>Back to Courses</button></div></div>;

 const enroll=()=>{ if(!course.enrolled){addCourse(course.id);pushToast('Course added to My Subjects','success');} };
 const moduleProgress=(m:CourseModule)=>{
   const q=moduleQuizzes.find(x=>x.moduleId===m.id);
   return calculateModuleProgress(m, q?.id, progress);
 };

 return <div className="page-stack">
   <div className="page-hero">
     <div>
       <button className="link-btn" onClick={()=>navigate('/courses')}><ArrowLeft size={15}/>Back to Courses</button>
       <div className="eyebrow">{course.code} · {course.specialization || course.category}</div>
       <h1>{course.name}</h1>
       <p>{course.description}</p>
     </div>
     <div className="hero-actions">
       {!course.enrolled && <button className="btn primary" onClick={enroll}>Add to My Subjects</button>}
       {finalQuiz && <button className="btn secondary" onClick={()=>navigate(`/courses/${course.id}/quiz`)}><Trophy size={16}/>Final Quiz</button>}
     </div>
   </div>

   <div className="stats-grid">
     <div className="stat-card"><strong>{percent}%</strong><span>Overall progress</span></div>
     <div className="stat-card"><strong>{learningPct}%</strong><span>Learning progress</span></div>
     <div className="stat-card"><strong>{assessmentPct}%</strong><span>Assessment progress</span></div>
     <div className="stat-card"><strong>{summary.completedLessons}/{summary.totalLessons}</strong><span>Lessons complete</span></div>
   </div>

   <div className="content-card">
     <div className="section-heading"><div><div className="eyebrow">LEARNING PATH</div><h2>Modules & lessons</h2></div>
       {nextLesson && !courseComplete && <button className="btn primary" onClick={()=>{setLastCourseLesson(course.id,nextLesson.id); navigate(`/courses/${course.id}/lessons/${nextLesson.id}`);}}><PlayCircle size={16}/>{lastId ? 'Continue learning' : 'Start course'}</button>}
       {courseComplete && <span className="soft-badge"><CheckCircle2 size={14}/>Course completed</span>}
     </div>
     <div className="progress-track large"><span style={{width:`${percent}%`}}/></div>
     <div className="text-xs muted mt-2">70% lesson completion + 30% quiz completion. Quiz completion is based on attempt, not score.</div>
     <div className="course-module-list">
       {modules.map((m,mi)=>{
         const isOpen=open===m.id || (open===null && mi===0);
         const mp=moduleProgress(m);
         const mq=moduleQuizzes.find(q=>q.moduleId===m.id);
         return <div className="course-module" key={m.id}>
           <button className="course-module-header" onClick={()=>setOpen(isOpen?null:m.id)}>
             <span className="module-index">{String(mi+1).padStart(2,'0')}</span>
             <span className="module-title"><strong>{m.title}</strong><small>{m.coverage || m.content || 'Course lesson'} · {mp}% module progress</small></span>
             {isOpen?<ChevronDown size={18}/>:<ChevronRight size={18}/>}
           </button>
           {isOpen && <div className="course-lessons">
             {m.lessons.map(l=>{
               const done=completed.has(l.id);
               return <div className="course-lesson" id={`lesson-${l.id}`} key={l.id}>
                 <button className={`lesson-check ${done?'done':''}`} onClick={()=>markCourseLesson(course.id,l.id,!done)} title={done?'Mark incomplete':'Mark complete'}>
                   {done?<CheckCircle2 size={18}/>:<Circle size={18}/>}
                 </button>
                 <div className="flex-1"><div className="eyebrow">LESSON {mi+1}</div><h3>{l.title}</h3><p className="lesson-summary">{m.coverage || 'Structured learning lesson with definitions, examples, applications and revision points.'}</p></div>
                 <button className="btn subtle" onClick={()=>{setLastCourseLesson(course.id,l.id);navigate(`/courses/${course.id}/lessons/${l.id}`)}}><PlayCircle size={15}/>Open Lesson</button>
               </div>
             })}
             {mq && <div className="course-quiz-callout"><div><div className="eyebrow">MODULE ASSESSMENT</div><strong>{mq.title}</strong><p>{mq.questions.length} questions · {completedQuizIds.has(mq.id)?'Completed':'Not completed'}</p></div><button className="btn primary" onClick={()=>navigate(`/courses/${course.id}/modules/${m.id}/quiz`)}><Trophy size={15}/>{completedQuizIds.has(mq.id)?'Review / Retry':'Start Module Quiz'}</button></div>}
           </div>}
         </div>
       })}
     </div>
   </div>

   {finalQuiz && <div className="content-card">
     <div className="section-heading"><div><div className="eyebrow">FINAL ASSESSMENT</div><h2>{finalQuiz.title}</h2><p className="muted">Comprehensive assessment across the course modules.</p></div>
       <button className="btn primary" onClick={()=>navigate(`/courses/${course.id}/quiz`)}><Trophy size={15}/>{completedQuizIds.has(finalQuiz.id)?'Review / Retry':'Start Final Quiz'}</button>
     </div>
     <div className="stats-grid">
       <div className="stat-card"><strong>{finalQuiz.questions.length}</strong><span>Questions</span></div>
       <div className="stat-card"><strong>{completedQuizIds.has(finalQuiz.id)?'Completed':'Pending'}</strong><span>Status</span></div>
       <div className="stat-card"><strong>{moduleQuizzes.length}</strong><span>Module quizzes</span></div>
       <div className="stat-card"><strong>{percent}%</strong><span>Overall progress</span></div>
     </div>
   </div>}

   <div className="text-xs muted flex items-center gap-2"><Clock3 size={14}/>Course data, progress, module quizzes and final quiz results are stored locally and synchronized with your account workspace.</div>
 </div>;
}
