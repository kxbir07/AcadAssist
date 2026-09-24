// AcadAssist Project Data — Curriculum Baseline & Sample Dataset
// All scores, progress percentages, and activity histories below are explicitly marked as Sample / Demo Data.

export interface UserProfile {
  name: string;
  fullName: string;
  role: string;
  field: string;
  academicLevel: string;
  email: string;
  location: string;
  memberSince: string;
  bio: string;
  tags: string[];
  quote: string;
  streakDays: number;
  streakStatus: string;
  cgpa: string;
  isDemo?: boolean;
}

export interface StatsSummary {
  dayStreak: number;
  topicsCompleted: number;
  hoursStudied: number;
  averageScore: number;
  notesLearned: number;
  questionsPracticed: number;
  totalStudyTime: number;
  overallProgress: number;
  notesIncrease: string;
  questionsIncrease: string;
  studyTimeIncrease: string;
  progressIncrease: string;
  isDemo?: boolean;
}

export interface Subject {
  id: string;
  name: string;
  fullName: string;
  documentsCount: number;
  progress: number;
  topicsCompleted: number;
  totalTopics: number;
  color: string;
  tag: string;
  code?: string;
  semester?: string;
  examDate?: string;
  importance?: 'Low' | 'Medium' | 'High';
}

export interface StudyPlanItem {
  id: string;
  time: string;
  title: string;
  description: string;
  subject: string;
  tag: string;
  duration: string;
  status: 'completed' | 'pending';
  actionLabel: string;
  color: string;
  icon: string;
}

export interface PlannerTask {
  id: string;
  time: string;
  title: string;
  description: string;
  subjectTag: string;
  duration: string;
  completed: boolean;
  type: 'study' | 'practice' | 'break' | 'quiz';
}

export interface Exam {
  id: string;
  subject: string;
  examName: string;
  daysLeft: number;
  dateStr: string;
  urgency: 'urgent' | 'high' | 'medium' | 'normal';
  icon: string;
}

export interface Deadline {
  title: string;
  daysLeft: string;
  dateStr: string;
  urgency: 'urgent' | 'high' | 'medium' | 'normal';
}

export interface KnowledgeMaterial {
  id?: string;
  name: string;
  subject: string;
  subjectId?: string;
  courseId?: string;
  type: 'PDF' | 'PPT' | 'DOCX' | 'TXT';
  size: string;
  addedOn: string;
  status: string;
  /** Raw backend processing status ('uploaded'|'queued'|'processing'|'processed'|'failed'),
   *  used to gate whether the document can actually be used for quiz/chat/summary generation.
   *  `status` above is only the human-readable label. */
  rawStatus?: string;
  starred: boolean;
  isDemo?: boolean;
}

export interface Activity {
  iconColor: string;
  text: string;
  time: string;
  action: string;
}

export interface AssessmentPerformance {
  averageScore: number;
  delta: string;
  questionsAttempted: number;
  correctAnswers: number;
  topicsCovered: number;
  isDemo?: boolean;
}

export interface RecentAttempt {
  topic: string;
  difficulty: string;
  scoreFraction: string;
  percentage: string;
  date: string;
  status: 'excellent' | 'passed' | 'average' | 'failed';
}

export interface PracticeSet {
  title: string;
  subtitle: string;
  questionsCount: number;
  type: string;
  icon: string;
  color: string;
}

export interface Milestone {
  title: string;
  date: string;
  completed: boolean;
}

export interface Badge {
  name: string;
  icon: string;
  color: string;
  unlocked: boolean;
}

export interface HelpCategory {
  title: string;
  description: string;
  icon: string;
  color: string;
}

export interface SystemStatus {
  name: string;
  status: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  time: string;
  text: string;
  sources?: Array<{
    chunk_id?: string;
    document_title?: string;
    title?: string;
    filename?: string;
    page_number?: number;
    slide_number?: number;
    score?: number;
    content_snippet?: string;
    citation?: string;
  }>;
  actions?: Array<{
    type: string;
    description: string;
    payload?: Record<string, any>;
  }>;
}

// ─── SAMPLE USER PROFILE (DEMO STUDENT) ───────────────────────────────────────

export const USER_PROFILE: UserProfile = {
  name: 'Student',
  fullName: 'AcadAssist Student',
  role: 'Undergraduate Student',
  field: 'Computer Science & Engineering',
  academicLevel: 'Undergraduate Degree Program',
  email: '',
  location: 'University Campus',
  memberSince: 'Recently',
  bio: 'Personal workspace. Managing course documents, solving daily quizzes, and tracking revision progress for exams.',
  tags: ['Operating Systems', 'Computer Networks', 'Database Systems', 'Algorithms'],
  quote: 'Consistent daily focus beats last-minute cramming.',
  streakDays: 0,
  streakStatus: 'Starting streak',
  cgpa: 'N/A',
  isDemo: false,
};

export const STATS_SUMMARY: StatsSummary = {
  dayStreak: 0,
  topicsCompleted: 0,
  hoursStudied: 0,
  averageScore: 0,
  notesLearned: 0,
  questionsPracticed: 0,
  totalStudyTime: 0,
  overallProgress: 0,
  notesIncrease: '0 this week',
  questionsIncrease: '0 this week',
  studyTimeIncrease: '0 this week',
  progressIncrease: '0 this week',
  isDemo: false,
};

// ─── CORE CURRICULUM SUBJECTS ────────────────────────────────────────────────

export const SUBJECTS: Subject[] = [
  {
    id: 'os',
    name: 'Operating Systems',
    fullName: 'Operating Systems (CSE-302)',
    documentsCount: 0,
    progress: 0,
    topicsCompleted: 0,
    totalTopics: 6,
    color: '#315c8b',
    tag: 'OS',
    code: 'CSE-302',
    semester: 'Semester 5',
    importance: 'High',
  },
  {
    id: 'cn',
    name: 'Computer Networks',
    fullName: 'Computer Networks (CSE-304)',
    documentsCount: 0,
    progress: 0,
    topicsCompleted: 0,
    totalTopics: 5,
    color: '#8b5a31',
    tag: 'CN',
    code: 'CSE-304',
    semester: 'Semester 5',
    importance: 'High',
  },
  {
    id: 'dbms',
    name: 'Database Management Systems',
    fullName: 'Database Management Systems (CSE-305)',
    documentsCount: 0,
    progress: 0,
    topicsCompleted: 0,
    totalTopics: 5,
    color: '#6a4c93',
    tag: 'DBMS',
    code: 'CSE-305',
    semester: 'Semester 5',
    importance: 'Medium',
  },
  {
    id: 'dsa',
    name: 'Data Structures & Algorithms',
    fullName: 'Data Structures & Algorithms (CSE-201)',
    documentsCount: 0,
    progress: 0,
    topicsCompleted: 0,
    totalTopics: 6,
    color: '#2d5f47',
    tag: 'DSA',
    code: 'CSE-201',
    semester: 'Semester 3',
    importance: 'High',
  },
  {
    id: 'ml',
    name: 'Machine Learning',
    fullName: 'Machine Learning (CSE-401)',
    documentsCount: 0,
    progress: 0,
    topicsCompleted: 0,
    totalTopics: 6,
    color: '#a14b5d',
    tag: 'ML',
    code: 'CSE-401',
    semester: 'Semester 7',
    importance: 'Medium',
  },
  {
    id: 'python',
    name: 'Python Programming',
    fullName: 'Python Programming (CS-101)',
    documentsCount: 0,
    progress: 0,
    topicsCompleted: 0,
    totalTopics: 6,
    color: '#b17b24',
    tag: 'PY',
    code: 'CS-101',
    semester: 'Semester 1',
    examDate: new Date(Date.now() + 38 * 86400000).toISOString().split('T')[0],
    importance: 'Low',
  },
];

export const TODAY_STUDY_PLAN: StudyPlanItem[] = [
  {
    id: 'plan-1',
    time: '09:00 AM',
    title: 'OS Deadlock Coffman Conditions',
    description: 'Review mutual exclusion, hold and wait, no preemption, circular wait',
    subject: 'Operating Systems',
    tag: 'OS',
    duration: '45 min',
    status: 'completed',
    actionLabel: 'Review',
    color: '#315c8b',
    icon: 'file-text',
  },
  {
    id: 'plan-2',
    time: '11:30 AM',
    title: 'TCP vs UDP Sliding Window & Flow Control',
    description: 'Solve 10 diagnostic questions on three-way handshakes and segment headers',
    subject: 'Computer Networks',
    tag: 'CN',
    duration: '40 min',
    status: 'pending',
    actionLabel: 'Start',
    color: '#8b5a31',
    icon: 'code',
  },
  {
    id: 'plan-3',
    time: '02:30 PM',
    title: 'B+ Tree Indexing & Node Splitting',
    description: 'Derive search depth and block pointers for clustered index queries',
    subject: 'Database Management Systems',
    tag: 'DBMS',
    duration: '50 min',
    status: 'pending',
    actionLabel: 'Start',
    color: '#6a4c93',
    icon: 'database',
  },
  {
    id: 'plan-4',
    time: '05:00 PM',
    title: 'Binary Search Tree Balancing Practice',
    description: 'AVL tree rotations and inorder traversal complexity',
    subject: 'Data Structures & Algorithms',
    tag: 'DSA',
    duration: '30 min',
    status: 'pending',
    actionLabel: 'Start',
    color: '#2d5f47',
    icon: 'check-square',
  },
];

export const PLANNER_TIMELINE_TASKS: PlannerTask[] = [];

export const UPCOMING_EXAMS: Exam[] = [];

export const UPCOMING_DEADLINES: Deadline[] = [];

export const KNOWLEDGE_MATERIALS: KnowledgeMaterial[] = [];

export const RECENT_ACTIVITIES: Activity[] = [];

export const ASSESSMENT_PERFORMANCE: AssessmentPerformance = {
  averageScore: 0,
  delta: 'No attempts yet',
  questionsAttempted: 0,
  correctAnswers: 0,
  topicsCovered: 0,
  isDemo: false,
};

export const RECENT_ATTEMPTS: RecentAttempt[] = [];

export const POPULAR_PRACTICE_SETS: PracticeSet[] = [
  { title: 'Operating Systems Core', subtitle: 'Processes, CPU Scheduling, Deadlocks, Memory Management', questionsCount: 40, type: 'Mixed', icon: 'cpu', color: '#315c8b' },
  { title: 'Computer Networks Protocols', subtitle: 'TCP, UDP, Subnetting, IP Addressing, Routing Algorithms', questionsCount: 35, type: 'Mixed', icon: 'share-2', color: '#8b5a31' },
  { title: 'Database Relational Design', subtitle: 'ER Models, Functional Dependencies, Normalization, Indexing', questionsCount: 30, type: 'Mixed', icon: 'database', color: '#6a4c93' },
  { title: 'Algorithms & Complexity', subtitle: 'Asymptotic Analysis, Trees, Graphs, Sorting & Searching', questionsCount: 45, type: 'Mixed', icon: 'code', color: '#2d5f47' },
];

export const MILESTONES: Milestone[] = [];

export const BADGES: Badge[] = [
  { name: 'Consistent Focus', icon: 'calendar', color: '#2d5f47', unlocked: false },
  { name: 'Systems Scholar', icon: 'cpu', color: '#315c8b', unlocked: false },
  { name: 'Problem Solver', icon: 'award', color: '#8b5a31', unlocked: false },
  { name: 'Knowledge Curator', icon: 'book-open', color: '#6a4c93', unlocked: false },
  { name: 'Exam Ready', icon: 'shield', color: '#a14b5d', unlocked: false },
];

export const STUDY_GOALS: Array<{ id: string; text: string; completed: boolean }> = [];

export const HELP_CATEGORIES: HelpCategory[] = [
  { title: 'Knowledge Base', description: 'Upload notes, organize subject files, and manage your library.', icon: 'book-open', color: '#2d5f47' },
  { title: 'Assessments & Quizzes', description: 'Create adaptive quizzes, diagnostic runs, and track score analytics.', icon: 'file-text', color: '#315c8b' },
  { title: 'Study Planner', description: 'Schedule exam blocks, set focus intervals, and sync project deadlines.', icon: 'calendar', color: '#8b5a31' },
  { title: 'AI Assistant', description: 'Concept clarifications, step-by-step problem breakdown and exam notes.', icon: 'sparkles', color: '#6a4c93' },
  { title: 'Account & Preferences', description: 'Manage appearance themes, notification preferences and profile info.', icon: 'settings', color: '#a14b5d' },
  { title: 'Data & Privacy', description: 'Local storage policies, export local workspace, and future cloud sync.', icon: 'shield', color: '#10b981' },
];

export const SYSTEM_STATUS_ITEMS: SystemStatus[] = [
  { name: 'Document Ingestion Service', status: 'Ready (Local Cache)' },
  { name: 'Deterministic Question Engine', status: 'Operational' },
  { name: 'Local Study Store', status: 'Optimal' },
  { name: 'Azure AI Foundry Boundary', status: 'Integration Ready' },
];

export const CHAT_HISTORY_INITIAL: ChatMessage[] = [
  {
    role: 'user',
    time: '10:14 AM',
    text: 'Can you explain the difference between Deadlock Prevention and Deadlock Avoidance in Operating Systems?',
  },
  {
    role: 'assistant',
    time: '10:15 AM',
    text: `### Deadlock Prevention vs. Deadlock Avoidance

Both techniques aim to prevent deadlocks, but they approach the problem differently:

1. **Deadlock Prevention (Static Approach)**
   - **Mechanism**: Eliminates at least one of the four Coffman conditions (*Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait*) before runtime.
   - **Example**: Impose a strict linear ordering on all resources. If every process must acquire resource $R_i$ before $R_j$ whenever $i < j$, circular wait is mathematically impossible.
   - **Trade-off**: Highly conservative; causes low device utilization and restricts process concurrency.

2. **Deadlock Avoidance (Dynamic Approach)**
   - **Mechanism**: The OS examines resource requests at runtime and only grants a request if the allocation leaves the system in a **Safe State**.
   - **Example**: Dijkstra's **Banker's Algorithm**, which checks if there is at least one sequence of processes that can run to completion with remaining resources.
   - **Trade-off**: Requires processes to declare their maximum resource requirements upfront.

*Exam Tip*: When asked for differences, contrast the **upfront constraints** of prevention against the **runtime evaluation** of avoidance.`,
  },
];

export const WEEKLY_STUDY_HOURS = [
  { day: 'Mon', hours: 3.5 },
  { day: 'Tue', hours: 4.2 },
  { day: 'Wed', hours: 2.8 },
  { day: 'Thu', hours: 5.0 },
  { day: 'Fri', hours: 4.5 },
  { day: 'Sat', hours: 3.0 },
  { day: 'Sun', hours: 3.5 },
];

export const ACTIVITY_DISTRIBUTION = [
  { name: 'Concept Study', value: 40, color: '#315c8b' },
  { name: 'Practice Quizzes', value: 25, color: '#2d5f47' },
  { name: 'Document Review', value: 20, color: '#8b5a31' },
  { name: 'AI Assistance', value: 15, color: '#6a4c93' },
];

const _calcRelDateStr = (daysAgo: number) => {
  const d = new Date(Date.now() - daysAgo * 86400000);
  return d.toLocaleDateString('en-US', { day: '2-digit', month: 'short' });
};

export const PROGRESS_OVER_TIME = [
  { date: _calcRelDateStr(28), progress: 30 },
  { date: _calcRelDateStr(21), progress: 42 },
  { date: _calcRelDateStr(14), progress: 54 },
  { date: _calcRelDateStr(7), progress: 61 },
  { date: _calcRelDateStr(0), progress: 64 },
];

export const SUBJECT_PROGRESS = [
  { name: 'Operating Systems', progress: 61, icon: 'cpu', color: '#315c8b' },
  { name: 'Data Structures & Algorithms', progress: 52, icon: 'code', color: '#2d5f47' },
  { name: 'Computer Networks', progress: 43, icon: 'share-2', color: '#8b5a31' },
  { name: 'Database Management Systems', progress: 28, icon: 'database', color: '#6a4c93' },
  { name: 'Machine Learning', progress: 18, icon: 'zap', color: '#a14b5d' },
  { name: 'Python Programming', progress: 75, icon: 'terminal', color: '#b17b24' },
];

export const INTERESTS = [
  { name: 'Systems Architecture', icon: 'cpu' },
  { name: 'Distributed Systems', icon: 'globe' },
  { name: 'Database Engines', icon: 'database' },
  { name: 'Algorithm Design', icon: 'code' },
  { name: 'Machine Learning', icon: 'zap' },
];
