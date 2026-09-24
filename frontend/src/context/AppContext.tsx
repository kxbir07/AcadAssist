import { createContext, useContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  STATS_SUMMARY, SUBJECTS, UPCOMING_EXAMS, UPCOMING_DEADLINES,
  RECENT_ACTIVITIES, ASSESSMENT_PERFORMANCE, RECENT_ATTEMPTS, POPULAR_PRACTICE_SETS,
  MILESTONES, BADGES, HELP_CATEGORIES, SYSTEM_STATUS_ITEMS, WEEKLY_STUDY_HOURS,
  ACTIVITY_DISTRIBUTION, PROGRESS_OVER_TIME, SUBJECT_PROGRESS, INTERESTS,
  type UserProfile, type StudyPlanItem, type PlannerTask, type KnowledgeMaterial, type ChatMessage,
  type Subject,
} from '../data/mockData';
import {
  fetchWeakTopics, fetchStudyRecommendation, fetchTodayPlan, updateTaskStatus,
  fetchDocuments, fetchNotes, createNote, updateNote as apiUpdateNote, deleteNote as apiDeleteNote,
  fetchChatHistory, appendChatMessage, clearBackendChatHistory,
  fetchPerformanceMetrics, fetchUpcomingExams, fetchQuizAttempts, displayDocumentStatus,
  type WeakTopic, type StudyRecommendation, type PerformanceMetrics, type BackendUpcomingExam, type QuizAttemptRecord,
} from '../services/api';
import * as auth from '../services/auth';

export interface Course {
  id: string; name: string; code: string; category: string; description: string;
  topics: string[]; progress: number; enrolled: boolean; level: 'Beginner'|'Intermediate'|'Advanced';
  color: string; estimatedHours: number;
}
export interface Note { id: string; title: string; subject: string; source: string; content: string; type: 'AI Notes'|'Summary'|'Exam Notes'|'Easy Explanation'; createdAt: string; }
export interface QuizQuestion { id: string; text: string; options: string[]; answer: number; explanation: string; }
export interface Quiz { id: string; title: string; source: string; subject: string; difficulty: 'Easy'|'Medium'|'Hard'|'Mixed'|'Adaptive'; questions: QuizQuestion[]; score?: number; completedAt?: string; }
export interface CalendarEvent { id: string; date: string; title: string; type: 'Task'|'Exam'|'Class'|'Assignment'|'Study Session'|'Personal Event'; time?: string; subject?: string; completed?: boolean; notes?: string; }
export interface Notification { id: string; title: string; message: string; type: 'success'|'warning'|'info'; read: boolean; createdAt: string; link?: string; }
export interface Toast { id: string; message: string; type: 'success'|'error'|'info'; }

const COURSES: Course[] = [
  {id:'os',name:'Operating Systems',code:'CSE-302',category:'Computer Science',description:'Processes, CPU scheduling, deadlocks, memory management and file systems.',topics:['Processes & Threads','CPU Scheduling','Memory Management','Deadlocks','File Systems','Virtual Memory'],progress:0,enrolled:true,level:'Intermediate',color:'#315c8b',estimatedHours:36},
  {id:'cn',name:'Computer Networks',code:'CSE-304',category:'Computer Science',description:'Networking fundamentals from physical transmission to application protocols.',topics:['Data Link','Network Layer & IP','Transport Layer (TCP/UDP)','Application Layer','Network Security'],progress:0,enrolled:true,level:'Intermediate',color:'#8b5a31',estimatedHours:34},
  {id:'dbms',name:'Database Management Systems',code:'CSE-305',category:'Computer Science',description:'Relational models, SQL, normalization, transactions and B+ tree indexing.',topics:['ER Models','SQL Queries','Normalization (1NF-BCNF)','Transactions & ACID','Indexing & B+ Trees'],progress:0,enrolled:true,level:'Intermediate',color:'#6a4c93',estimatedHours:30},
  {id:'dsa',name:'Data Structures & Algorithms',code:'CSE-201',category:'Computer Science',description:'Core data structures, algorithms, asymptotic complexity and problem solving.',topics:['Arrays & Strings','Linked Lists','Stacks & Queues','Trees & AVL','Graphs (BFS/DFS)','Sorting & Searching'],progress:0,enrolled:true,level:'Intermediate',color:'#2d5f47',estimatedHours:42},
  {id:'ml',name:'Machine Learning',code:'CSE-401',category:'AI & ML',description:'Supervised and unsupervised learning with practical model intuition.',topics:['Linear Regression','Logistic Regression','Decision Trees','SVM','Clustering','Neural Networks'],progress:0,enrolled:false,level:'Advanced',color:'#a14b5d',estimatedHours:48},
  {id:'python',name:'Python Programming',code:'CS-101',category:'Programming',description:'Python fundamentals, data structures, functions, OOP and exception handling.',topics:['Syntax & Types','Functions & Scope','Collections','OOP Principles','File I/O','Modules'],progress:0,enrolled:false,level:'Beginner',color:'#b17b24',estimatedHours:24},
];

function readStorage<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function writeStorage(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage is optional */
  }
}

interface AppState {
  user: UserProfile;
  todayPlan: StudyPlanItem[];
  plannerTasks: PlannerTask[];
  knowledgeMaterials: KnowledgeMaterial[];
  chatHistory: ChatMessage[];
  settings: { dailyReminder:boolean; examAlerts:boolean; streakUpdates:boolean; assessmentFeedback:boolean; progressReport:boolean; newFeatures:boolean; theme:'light'|'dark'|'system'; accentColor:string; fontSize:'small'|'medium'|'large'; defaultStudyDuration:number; preferredDifficulty:'Easy'|'Medium'|'Hard'|'Mixed' };
  sidebarOpen:boolean;
  studyGoals: Array<{ id: string; text: string; completed: boolean }>;
  courses:Course[];
  notes:Note[];
  quizzes:Quiz[];
  events:CalendarEvent[];
  notifications:Notification[];
  toasts:Toast[];
  subjects:Subject[];
  weakTopics:WeakTopic[];
  studyRecommendation:StudyRecommendation|null;
  upcomingExams:BackendUpcomingExam[];
  performanceMetrics:PerformanceMetrics|null;
  quizAttempts:QuizAttemptRecord[];
}

interface AppContextType extends AppState {
  updateUser:(patch:Partial<UserProfile>)=>void;
  togglePlanItem:(id:string)=>void;
  togglePlannerTask:(id:string)=>void;
  toggleGoal:(id:string)=>void;
  addChatMessage:(role:'user'|'assistant',text:string,sources?:any[],actions?:any[])=>void;
  clearChatHistory:()=>void;
  addKnowledgeMaterial:(material:KnowledgeMaterial)=>void;
  updateKnowledgeMaterial:(idOrName:string,patch:Partial<KnowledgeMaterial>)=>void;
  deleteKnowledgeMaterial:(idOrName:string)=>void;
  updateSetting:(key:string,value:unknown)=>void;
  setSidebarOpen:(open:boolean)=>void;
  addCourse:(id:string)=>void;
  removeCourse:(id:string)=>void;
  addNote:(note:Note)=>void;
  updateNote:(id:string,patch:Partial<Note>)=>void;
  deleteNote:(id:string)=>void;
  addQuiz:(quiz:Quiz)=>void;
  updateQuiz:(id:string,patch:Partial<Quiz>)=>void;
  addEvent:(event:CalendarEvent)=>void;
  updateEvent:(id:string,patch:Partial<CalendarEvent>)=>void;
  deleteEvent:(id:string)=>void;
  addSubject:(subject:Subject)=>void;
  updateSubject:(id:string,patch:Partial<Subject>)=>void;
  deleteSubject:(id:string)=>void;
  markNotificationsRead:()=>void;
  markNotificationRead:(id:string)=>void;
  pushToast:(message:string,type?:Toast['type'])=>void;
  dismissToast:(id:string)=>void;
  reloadWeakTopics:()=>Promise<void>;
  reloadAppData:()=>Promise<void>;
}

const AppContext=createContext<AppContextType|null>(null);

const defaultSettings: AppState['settings'] = {
  dailyReminder:true, examAlerts:true, streakUpdates:true, assessmentFeedback:true,
  progressReport:true, newFeatures:false, theme:'light', accentColor:'#2d5f47', fontSize:'medium',
  defaultStudyDuration:50, preferredDifficulty:'Mixed'
};

function getInitialUser(): UserProfile {
  const cached = auth.getCachedUser();
  return {
    name: cached?.name || 'Student',
    fullName: cached?.name || 'AcadAssist Student',
    role: cached?.role || 'Student',
    field: cached?.fieldOfStudy || 'Computer Science',
    academicLevel: cached?.academicLevel || 'Undergraduate',
    email: cached?.email || '',
    location: 'Campus',
    memberSince: 'Recently',
    bio: cached?.bio || 'AcadAssist Scholar',
    tags: ['Computer Science'],
    quote: 'Focused study, compounding progress.',
    streakDays: 0,
    streakStatus: 'Starting streak',
    cgpa: 'N/A',
  };
}


export function AppProvider({children}:{children:ReactNode}) {
  const [user,setUser]=useState<UserProfile>(getInitialUser);
  const [todayPlan,setTodayPlan]=useState<StudyPlanItem[]>([]);
  const [plannerTasks,setPlannerTasks]=useState<PlannerTask[]>([]);
  const [knowledgeMaterials,setKnowledgeMaterials]=useState<KnowledgeMaterial[]>([]);
  const [chatHistory,setChatHistory]=useState<ChatMessage[]>([]);
  const [studyGoals,setStudyGoals]=useState<AppState['studyGoals']>([]);
  const [courses,setCourses]=useState<Course[]>(COURSES);
  const [notes,setNotes]=useState<Note[]>([]);
  const [quizzes,setQuizzes]=useState<Quiz[]>([]);
  const [events,setEvents]=useState<CalendarEvent[]>([]);
  const [notifications,setNotifications]=useState<Notification[]>([]);
  const [toasts,setToasts]=useState<Toast[]>([]);
  const [subjects,setSubjects]=useState<Subject[]>(SUBJECTS);
  const [sidebarOpen,setSidebarOpen]=useState(false);
  const [settings,setSettings]=useState<AppState['settings']>(()=>{
    const stored = readStorage<Partial<AppState['settings']>>('acadassist.settings', {});
    const theme: AppState['settings']['theme'] = stored.theme === 'dark' ? 'dark' : 'light';
    return {
      ...defaultSettings,
      ...stored,
      theme,
    };
  });
  
  const [weakTopics,setWeakTopics]=useState<WeakTopic[]>([]);
  const [studyRecommendation,setStudyRecommendation]=useState<StudyRecommendation|null>(null);
  const [upcomingExams,setUpcomingExams]=useState<BackendUpcomingExam[]>([]);
  const [performanceMetrics,setPerformanceMetrics]=useState<PerformanceMetrics|null>(null);
  const [quizAttempts,setQuizAttempts]=useState<QuizAttemptRecord[]>([]);

  const reloadAppData=useCallback(async()=>{
    if (!auth.getToken()) {
      return;
    }
    try {
      const [docs, backendNotes, todayData, chatMsgs, topics, rec, exams, perf, attempts] = await Promise.all([
        fetchDocuments(),
        fetchNotes(),
        fetchTodayPlan(),
        fetchChatHistory(),
        fetchWeakTopics(),
        fetchStudyRecommendation(),
        fetchUpcomingExams(),
        fetchPerformanceMetrics(),
        fetchQuizAttempts(),
      ]);

      if (docs) {
        setKnowledgeMaterials(
          docs.map(d => {
            const matchedSubj = COURSES.find(c => c.id === d.subjectId || c.code.toLowerCase() === (d.courseId || '').toLowerCase() || c.id === d.courseId);
            return {
              id: d.id,
              name: d.name,
              subject: matchedSubj?.name || 'Operating Systems',
              subjectId: d.subjectId,
              courseId: d.courseId,
              type: (d.type.toLowerCase().includes('pdf') ? 'PDF' : d.type.toLowerCase().includes('ppt') ? 'PPT' : d.type.toLowerCase().includes('doc') ? 'DOCX' : 'TXT') as KnowledgeMaterial['type'],
              size: `${(d.size / 1024 / 1024).toFixed(1)} MB`,
              addedOn: d.uploadedAt,
              status: displayDocumentStatus(d.status),
              rawStatus: d.status,
              starred: false,
            };
          })
        );
      }

      if (backendNotes) {
        setNotes(
          backendNotes.map(n => ({
            id: n.id,
            title: n.title,
            subject: n.subject || 'General',
            source: 'Notes',
            type: (n.note_type as any) || 'Summary',
            content: n.content,
            createdAt: n.created_at ? new Date(n.created_at).toLocaleDateString() : 'Recently',
          }))
        );
      }

      if (todayData?.tasks && todayData.tasks.length > 0) {
        setTodayPlan(
          todayData.tasks.map(t => ({
            id: t.task_id,
            time: t.start_time || '09:00 AM',
            title: t.title,
            description: t.description || '',
            subject: t.subject_id || 'Academic Study',
            tag: 'STUDY',
            duration: `${t.duration_minutes} min`,
            status: t.status === 'completed' ? 'completed' : 'pending',
            actionLabel: 'Study',
            color: '#315c8b',
            icon: 'calendar',
          }))
        );
      }

      if (chatMsgs && chatMsgs.length > 0) {
        setChatHistory(
          chatMsgs.map(m => ({
            role: m.role as 'user' | 'assistant',
            text: m.text,
            time: m.time,
          }))
        );
      }

      setWeakTopics(topics);
      setStudyRecommendation(rec);
      setUpcomingExams(exams);
      setPerformanceMetrics(perf);
      setQuizAttempts(attempts);

      // Compute dynamic subject progress and document counts from actual user performance
      setSubjects(prev => prev.map(s => {
        const matchingCourse = COURSES.find(c => c.name === s.name);
        const docCount = docs ? docs.filter(d => 
          d.name.toLowerCase().includes(s.tag.toLowerCase()) || 
          d.name.toLowerCase().includes(s.id.toLowerCase()) ||
          d.name.toLowerCase().includes(s.name.toLowerCase())
        ).length : 0;

        if (perf && perf.topicMastery && Object.keys(perf.topicMastery).length > 0 && matchingCourse) {
          const topicKeys = Object.keys(perf.topicMastery);
          const masteredInSubject = topicKeys.filter(k => 
            matchingCourse.topics.some(t => t.toLowerCase().includes(k.toLowerCase()) || k.toLowerCase().includes(t.toLowerCase()))
          );
          if (masteredInSubject.length > 0) {
            const avgMastery = masteredInSubject.reduce((sum, k) => sum + (perf.topicMastery[k] || 0), 0) / masteredInSubject.length;
            return {
              ...s,
              documentsCount: docCount,
              progress: Math.round(avgMastery * 100),
              topicsCompleted: Math.min(s.totalTopics, masteredInSubject.length),
            };
          }
        }

        return {
          ...s,
          documentsCount: docCount,
        };
      }));
    } catch {
      // Keep state clean on network error
    }
  },[]);

  useEffect(()=>{
    reloadAppData();
  },[reloadAppData]);

  // Keep settings persisted in localStorage
  useEffect(()=>{ writeStorage('acadassist.settings',settings); },[settings]);

  useEffect(()=>{
    const root=document.documentElement;
    const applyTheme=(dark:boolean)=>{
      const t = dark ? 'dark' : 'light';
      document.body.dataset.theme=t;
      root.dataset.theme=t;
      if (dark) {
        root.classList.add('dark');
        document.body.classList.add('dark');
      } else {
        root.classList.remove('dark');
        document.body.classList.remove('dark');
      }
    };

    if(settings.theme==='system'){
      const media=typeof window!=='undefined'&&window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
      applyTheme(media ? media.matches : false);
      const listener=(e:MediaQueryListEvent)=>applyTheme(e.matches);
      media?.addEventListener?.('change',listener);
      return ()=>{
        media?.removeEventListener?.('change',listener);
      };
    } else {
      applyTheme(settings.theme==='dark');
    }
  },[settings.theme]);

  useEffect(()=>{
    const root=document.documentElement;
    root.style.setProperty('--color-green-accent',settings.accentColor);
    root.style.setProperty('--color-accent',settings.accentColor);
    root.style.setProperty('--app-font-size',settings.fontSize==='small'?'14px':settings.fontSize==='large'?'17px':'15px');
  },[settings.accentColor,settings.fontSize]);

  const updateUser=useCallback((patch:Partial<UserProfile>)=>setUser(p=>({...p,...patch})),[]);

  const togglePlanItem=useCallback((id:string)=>setTodayPlan(p=>p.map(x=>{
    if (x.id === id) {
      const nextStatus = x.status === 'completed' ? 'pending' : 'completed';
      updateTaskStatus(id, nextStatus).catch(() => {});
      return {...x, status: nextStatus};
    }
    return x;
  })),[]);

  const togglePlannerTask=useCallback((id:string)=>setPlannerTasks(p=>p.map(x=>{
    if (x.id === id) {
      const nextCompleted = !x.completed;
      updateTaskStatus(id, nextCompleted ? 'completed' : 'pending').catch(() => {});
      return {...x, completed: nextCompleted};
    }
    return x;
  })),[]);

  const toggleGoal=useCallback((id:string)=>setStudyGoals(p=>p.map(x=>x.id===id?{...x,completed:!x.completed}:x)),[]);

  const addChatMessage=useCallback((role:'user'|'assistant',text:string,sources?:any[],actions?:any[])=>{
    setChatHistory(p=>[...p,{role,text,sources,actions,time:new Date().toLocaleTimeString([], {hour:'numeric',minute:'2-digit'})}]);
    appendChatMessage(role, text).catch(() => {});
  },[]);

  const clearChatHistory=useCallback(()=>{
    setChatHistory([]);
    clearBackendChatHistory().catch(() => {});
  },[]);

  const addKnowledgeMaterial=useCallback((m:KnowledgeMaterial)=>setKnowledgeMaterials(p=>[m,...p]),[]);

  const updateKnowledgeMaterial=useCallback((key:string,patch:Partial<KnowledgeMaterial>)=>setKnowledgeMaterials(p=>p.map(m=>((m as KnowledgeMaterial & {id?:string}).id===key||m.name===key)?{...m,...patch}:m)),[]);

  const deleteKnowledgeMaterial=useCallback((key:string)=>setKnowledgeMaterials(p=>p.filter(m=>!((m as KnowledgeMaterial & {id?:string}).id===key||m.name===key))),[]);

  const updateSetting=useCallback((key:string,value:unknown)=>setSettings(p=>({...p,[key]:value})),[]);

  const addCourse=useCallback((id:string)=>setCourses(p=>p.map(c=>c.id===id?{...c,enrolled:true}:c)),[]);

  const removeCourse=useCallback((id:string)=>setCourses(p=>p.map(c=>c.id===id?{...c,enrolled:false}:c)),[]);

  const addNote=useCallback((n:Note)=>{
    setNotes(p=>[n,...p]);
    createNote({
      title: n.title,
      content: n.content,
      subject: n.subject,
      note_type: n.type,
    }).catch(() => {});
  },[]);

  const updateNote=useCallback((id:string,patch:Partial<Note>)=>{
    setNotes(p=>p.map(n=>n.id===id?{...n,...patch}:n));
    apiUpdateNote(id, {
      title: patch.title,
      content: patch.content,
      subject: patch.subject,
      note_type: patch.type,
    }).catch(() => {});
  },[]);

  const deleteNote=useCallback((id:string)=>{
    setNotes(p=>p.filter(n=>n.id!==id));
    apiDeleteNote(id).catch(() => {});
  },[]);

  const addQuiz=useCallback((q:Quiz)=>setQuizzes(p=>[q,...p]),[]);

  const updateQuiz=useCallback((id:string,patch:Partial<Quiz>)=>setQuizzes(p=>p.map(q=>q.id===id?{...q,...patch}:q)),[]);

  const addEvent=useCallback((e:CalendarEvent)=>setEvents(p=>[...p,e]),[]);

  const updateEvent=useCallback((id:string,patch:Partial<CalendarEvent>)=>setEvents(p=>p.map(e=>e.id===id?{...e,...patch}:e)),[]);

  const deleteEvent=useCallback((id:string)=>setEvents(p=>p.filter(e=>e.id!==id)),[]);

  const addSubject=useCallback((s:Subject)=>setSubjects(p=>[...p,s]),[]);

  const updateSubject=useCallback((id:string,patch:Partial<Subject>)=>setSubjects(p=>p.map(s=>s.id===id?{...s,...patch}:s)),[]);

  const deleteSubject=useCallback((id:string)=>setSubjects(p=>p.filter(s=>s.id!==id)),[]);

  const markNotificationsRead=useCallback(()=>setNotifications(p=>p.map(n=>({...n,read:true}))),[]);

  const markNotificationRead=useCallback((id:string)=>setNotifications(p=>p.map(n=>n.id===id?{...n,read:true}:n)),[]);

  const dismissToast=useCallback((id:string)=>setToasts(p=>p.filter(t=>t.id!==id)),[]);

  const pushToast=useCallback((message:string,type:Toast['type']='success')=>{
    const id=crypto.randomUUID();
    setToasts(p=>[...p,{id,message,type}]);
    window.setTimeout(()=>setToasts(p=>p.filter(t=>t.id!==id)),3500);
  },[]);

  const value=useMemo(()=>({
    user,todayPlan,plannerTasks,knowledgeMaterials,chatHistory,settings,sidebarOpen,studyGoals,
    courses,notes,quizzes,events,notifications,toasts,subjects,weakTopics,studyRecommendation,
    upcomingExams,performanceMetrics,quizAttempts,
    updateUser,togglePlanItem,togglePlannerTask,toggleGoal,addChatMessage,clearChatHistory,
    addKnowledgeMaterial,updateKnowledgeMaterial,deleteKnowledgeMaterial,updateSetting,setSidebarOpen,
    addCourse,removeCourse,addNote,updateNote,deleteNote,addQuiz,updateQuiz,addEvent,updateEvent,
    deleteEvent,addSubject,updateSubject,deleteSubject,markNotificationsRead,markNotificationRead,
    pushToast,dismissToast,reloadWeakTopics: reloadAppData,reloadAppData
  }),[
    user,todayPlan,plannerTasks,knowledgeMaterials,chatHistory,settings,sidebarOpen,studyGoals,
    courses,notes,quizzes,events,notifications,toasts,subjects,weakTopics,studyRecommendation,
    upcomingExams,performanceMetrics,quizAttempts,
    updateUser,togglePlanItem,togglePlannerTask,toggleGoal,addChatMessage,clearChatHistory,
    addKnowledgeMaterial,updateKnowledgeMaterial,deleteKnowledgeMaterial,updateSetting,addCourse,
    removeCourse,addNote,updateNote,deleteNote,addQuiz,updateQuiz,addEvent,updateEvent,deleteEvent,
    addSubject,updateSubject,deleteSubject,markNotificationsRead,markNotificationRead,pushToast,
    dismissToast,reloadAppData
  ]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(){const ctx=useContext(AppContext); if(!ctx) throw new Error('useApp must be used within AppProvider'); return ctx;}
export { STATS_SUMMARY,SUBJECTS,UPCOMING_EXAMS,UPCOMING_DEADLINES,RECENT_ACTIVITIES,ASSESSMENT_PERFORMANCE,RECENT_ATTEMPTS,POPULAR_PRACTICE_SETS,MILESTONES,BADGES,HELP_CATEGORIES,SYSTEM_STATUS_ITEMS,WEEKLY_STUDY_HOURS,ACTIVITY_DISTRIBUTION,PROGRESS_OVER_TIME,SUBJECT_PROGRESS,INTERESTS };
export { COURSES };