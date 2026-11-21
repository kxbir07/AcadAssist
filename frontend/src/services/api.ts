// Azure-ready API boundary. The UI never talks to Azure directly.
const API_BASE = import.meta.env.VITE_API_URL?.replace(/\/$/, '') || '';

export interface WeakTopic {
  id: string;
  topic: string;
  subject: string;
  accuracyScore: number;
  recommendedAction: string;
  examUrgency?: 'urgent' | 'high' | 'medium' | 'normal';
  examName?: string;
  daysToExam?: number;
  isDemo?: boolean;
}

export interface StudyRecommendation {
  subjectName: string;
  topicName: string;
  reason: string;
  suggestedDuration: string;
  actionType: 'quiz' | 'study' | 'notes';
  isDemo?: boolean;
}

function getAuthHeader(): Record<string, string> {
  try {
    const token = localStorage.getItem('acadassist.auth.token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = API_BASE ? `${API_BASE}${path}` : path;
  const response = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
      ...(init?.headers || {}),
    },
  });
  if (!response.ok) throw new Error((await response.text()) || `Request failed (${response.status})`);
  return response.json() as Promise<T>;
}

export interface ChatResult {
  text: string;
  sources?: Array<{
    chunk_id?: string;
    document_title?: string;
    title?: string;
    filename?: string;
    page_number?: number;
    score?: number;
    content_snippet?: string;
    citation?: string;
  }>;
  actions?: Array<{
    type: string;
    description: string;
    payload?: Record<string, any>;
  }>;
  executionMode?: string;
}

export async function sendChatMessage(
  message: string,
  materialId?: string,
  context?: { courseId?: string; subjectId?: string }
): Promise<ChatResult> {
  const payload: Record<string, any> = { message };
  if (materialId) payload.document_id = materialId;
  if (context?.courseId) payload.course_id = context.courseId;
  if (context?.subjectId) payload.subject_id = context.subjectId;

  const res = await request<{ message: string; sources?: any[]; actions?: any[]; execution_mode?: string }>('/api/chat', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return {
    text: res.message,
    sources: res.sources,
    actions: res.actions,
    executionMode: res.execution_mode,
  };
}

// Person 2: Document Management Endpoints (/api/documents)
export interface DocumentUploadResponse {
  id: string;
  name: string;
  size: number;
  type: string;
  url?: string;
  uploadedAt: string;
  subjectId?: string;
  courseId?: string;
  isDemo?: boolean;
  // Backend processing status: 'uploaded' | 'queued' | 'processing' | 'processed' | 'failed'
  status?: string;
}

export function displayDocumentStatus(status?: string): string {
  switch ((status || '').toLowerCase()) {
    case 'processed':
      return 'Processed · Ready';
    case 'processing':
      return 'Processing…';
    case 'queued':
      return 'Queued for Processing';
    case 'failed':
      return 'Processing Failed';
    case 'uploaded':
      return 'Stored Locally · Ready for Processing';
    default:
      return 'Processing…';
  }
}

export function isDocumentReady(status?: string): boolean {
  return (status || '').toLowerCase() === 'processed';
}

export async function fetchDocuments(): Promise<DocumentUploadResponse[] | null> {
  try {
    const res = await request<{
      documents: Array<{
        document_id: string;
        filename: string;
        title: string;
        file_type: string;
        status: string;
        size_bytes?: number;
        uploaded_at: string;
        subject_id?: string;
        course_id?: string;
      }>;
      total: number;
    }>('/api/documents');
    return res.documents.map(d => ({
      id: d.document_id,
      name: d.filename || d.title,
      size: d.size_bytes || 0,
      type: d.file_type || 'application/pdf',
      uploadedAt: d.uploaded_at,
      subjectId: d.subject_id,
      courseId: d.course_id,
      isDemo: false,
      status: d.status,
    }));
  } catch {
    return null;
  }
}

export async function uploadDocument(
  file: File | { name: string; size: number; type: string },
  courseId: string = 'cn',
  subjectId: string = 'cn',
): Promise<DocumentUploadResponse> {
  if (!(file instanceof File)) {
    throw new Error('A real File object is required for document upload.');
  }

  const formData = new FormData();
  formData.append('file', file);
  formData.append('course_id', courseId);
  formData.append('subject_id', subjectId);
  formData.append('title', file.name);
  formData.append('visibility', 'private');

  const url = API_BASE ? `${API_BASE}/api/documents` : '/api/documents';
  const token = localStorage.getItem('acadassist.auth.token');
  const response = await fetch(url, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  if (!response.ok) {
    throw new Error((await response.text()) || `Document upload failed (${response.status})`);
  }

  const data = await response.json();
  if (!data.document_id) {
    throw new Error('Document upload succeeded without a document ID.');
  }

  let processedStatus = data.status || 'uploaded';
  if (processedStatus !== 'processed') {
    try {
      const processUrl = API_BASE
        ? `${API_BASE}/api/documents/${encodeURIComponent(data.document_id)}/process`
        : `/api/documents/${encodeURIComponent(data.document_id)}/process`;
      const processRes = await fetch(processUrl, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (processRes.ok) {
        const processData = await processRes.json();
        processedStatus = processData.status || 'processed';
      } else {
        console.error('Document processing failed:', await processRes.text());
        processedStatus = 'failed';
      }
    } catch (err) {
      console.error('Failed to trigger document processing:', err);
      processedStatus = 'failed';
    }
  }

  return {
    id: data.document_id,
    name: data.filename || file.name,
    size: file.size,
    type: file.type || 'application/pdf',
    uploadedAt: data.uploaded_at || data.created_at || new Date().toISOString(),
    subjectId: data.subject_id || subjectId,
    courseId: data.course_id || courseId,
    isDemo: false,
    status: processedStatus,
  };
}

export async function fetchDocumentBlob(documentId: string): Promise<Blob> {
  const url = API_BASE
    ? `${API_BASE}/api/documents/${encodeURIComponent(documentId)}/download`
    : `/api/documents/${encodeURIComponent(documentId)}/download`;
  const token = localStorage.getItem('acadassist.auth.token');
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`Download failed with status ${res.status}`);
  return await res.blob();
}

export async function downloadDocument(documentId: string, filename: string): Promise<void> {
  const blob = await fetchDocumentBlob(documentId);
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = blobUrl;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
}

export async function deleteBackendDocument(documentId: string): Promise<boolean> {
  try {
    await request(`/api/documents/${encodeURIComponent(documentId)}`, {
      method: 'DELETE',
    });
    return true;
  } catch {
    return false;
  }
}

export interface DocumentSummaryResult {
  document_id: string;
  title: string;
  filename: string;
  mode: string;
  status: string;
  summary: string;
  total_chunks: number;
  sections: Array<{ section: string; page?: number; slide?: number; overview?: string }>;
}

export async function summarizeBackendDocument(
  documentId: string,
  mode: 'quick' | 'detailed' | 'exam' | 'revision' = 'quick'
): Promise<DocumentSummaryResult | null> {
  try {
    return await request<DocumentSummaryResult>(
      `/api/documents/${encodeURIComponent(documentId)}/summarize`,
      {
        method: 'POST',
        body: JSON.stringify({ mode }),
      }
    );
  } catch {
    return null;
  }
}

export interface KnowledgeChunkSearchResult {
  chunk_id: string;
  document_id: string;
  course_id: string;
  subject_id: string;
  content: string;
  document_title: string;
  section_title?: string | null;
  filename: string;
  page_number?: number | null;
  slide_number?: number | null;
  score: number;
}

export async function searchKnowledgeChunks(
  query: string,
  options?: { courseId?: string; subjectId?: string; topK?: number }
): Promise<KnowledgeChunkSearchResult[]> {
  if (!query.trim()) return [];
  try {
    const res = await request<{ results: KnowledgeChunkSearchResult[] }>('/api/knowledge/search', {
      method: 'POST',
      body: JSON.stringify({
        query: query.trim(),
        course_id: options?.courseId,
        subject_id: options?.subjectId,
        top_k: options?.topK || 6,
      }),
    });
    return res.results || [];
  } catch {
    return [];
  }
}

// Person 3 / Person 4: Weak Topics (/api/performance/weak-topics)
export async function fetchWeakTopics(): Promise<WeakTopic[]> {
  try {
    const res = await request<{
      topics?: Array<{
        topic_id: string;
        topic?: string;
        topic_name?: string;
        mastery?: number;
        accuracy_rate?: number;
        recommended_action?: string;
        recommended_difficulty?: string;
      }>;
    }>('/api/performance/weak-topics');
    if (res?.topics && res.topics.length > 0) {
      return res.topics.map(t => {
        const accuracy = t.mastery !== undefined ? t.mastery : (t.accuracy_rate !== undefined ? t.accuracy_rate : 0.5);
        const name = t.topic || t.topic_name || t.topic_id;
        return {
          id: t.topic_id,
          topic: name,
          subject: 'Academic Curriculum',
          accuracyScore: Math.round(accuracy * 100),
          recommendedAction: t.recommended_action || `Review ${name} core principles and solve practice problems.`,
          examUrgency: accuracy < 0.6 ? 'urgent' : 'high',
          isDemo: false,
        };
      });
    }
  } catch {
    // empty state
  }
  return [];
}

export async function fetchStudyRecommendation(): Promise<StudyRecommendation | null> {
  const recs = await fetchStudyRecommendations();
  return recs.length > 0 ? recs[0] : null;
}

export async function fetchStudyRecommendations(): Promise<StudyRecommendation[]> {
  try {
    const res = await request<{ recommendations?: Array<{ topic_name: string; reason: string; action: string; urgency: string }> }>(
      '/api/progress/recommendations'
    );
    if (res?.recommendations && res.recommendations.length > 0) {
      return res.recommendations.map(r => ({
        subjectName: 'Computer Science',
        topicName: r.topic_name,
        reason: r.reason,
        suggestedDuration: '45 min',
        actionType: (r.action?.toLowerCase().includes('quiz') ? 'quiz' : 'study') as 'quiz' | 'study',
        isDemo: false,
      }));
    }
  } catch {
    // empty state
  }
  return [];
}

export interface ProgressMetricsSummary {
  courseCompletion: number;
  subjectCompletion: number;
  topicMastery: Record<string, number>;
  quizAccuracy: number;
  studyConsistency: number;
  plannerCompletion: number;
  studyTimeMinutes: number;
  completedTopics: string[];
  remainingTopics: string[];
}

export async function fetchProgressSummary(courseId?: string, subjectId?: string): Promise<ProgressMetricsSummary | null> {
  try {
    const params = new URLSearchParams();
    if (courseId) params.set('course_id', courseId);
    if (subjectId) params.set('subject_id', subjectId);
    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await request<{
      course_completion: number;
      subject_completion: number;
      topic_mastery: Record<string, number>;
      quiz_accuracy: number;
      study_consistency: number;
      planner_completion: number;
      study_time: number;
      completed_topics: string[];
      remaining_topics: string[];
    }>(`/api/progress${qs}`);
    return {
      courseCompletion: res.course_completion,
      subjectCompletion: res.subject_completion,
      topicMastery: res.topic_mastery || {},
      quizAccuracy: res.quiz_accuracy,
      studyConsistency: res.study_consistency,
      plannerCompletion: res.planner_completion,
      studyTimeMinutes: res.study_time || 0,
      completedTopics: res.completed_topics || [],
      remainingTopics: res.remaining_topics || [],
    };
  } catch {
    return null;
  }
}

export interface PerformanceMetrics {
  userId: string;
  overallAccuracy: number;
  recentAccuracy: number;
  attemptCount: number;
  totalQuestionsAttempted: number;
  totalCorrect: number;
  totalIncorrect: number;
  topicMastery: Record<string, number>;
  topicAccuracy?: Record<string, number>;
  difficultyAccuracy?: Record<string, number>;
  weakTopics: Array<{ topicId: string; topic: string; mastery: number }>;
  strongTopics: Array<{ topicId: string; topic: string; mastery: number }>;
}

export async function fetchPerformanceMetrics(): Promise<PerformanceMetrics | null> {
  try {
    const res = await request<{
      user_id: string;
      overall_accuracy: number;
      recent_accuracy: number;
      attempt_count: number;
      total_questions_attempted: number;
      total_correct: number;
      total_incorrect: number;
      topic_mastery: Record<string, number>;
      topic_accuracy?: Record<string, number>;
      difficulty_accuracy?: Record<string, number>;
      weak_topics: Array<{ topic_id: string; topic: string; mastery: number }>;
      strong_topics: Array<{ topic_id: string; topic: string; mastery: number }>;
    }>('/api/performance');
    if (res) {
      return {
        userId: res.user_id,
        overallAccuracy: res.overall_accuracy,
        recentAccuracy: res.recent_accuracy,
        attemptCount: res.attempt_count,
        totalQuestionsAttempted: res.total_questions_attempted,
        totalCorrect: res.total_correct,
        totalIncorrect: res.total_incorrect,
        topicMastery: res.topic_mastery || {},
        topicAccuracy: res.topic_accuracy || {},
        difficultyAccuracy: res.difficulty_accuracy || {},
        weakTopics: (res.weak_topics || []).map(w => ({ topicId: w.topic_id, topic: w.topic, mastery: w.mastery })),
        strongTopics: (res.strong_topics || []).map(s => ({ topicId: s.topic_id, topic: s.topic, mastery: s.mastery })),
      };
    }
  } catch {
    // empty state
  }
  return null;
}

export interface BackendUpcomingExam {
  examId: string;
  userId: string;
  subjectId: string;
  title: string;
  examDate: string;
  daysUntilExam?: number;
  assessmentFocus?: string;
}

export async function fetchUpcomingExams(): Promise<BackendUpcomingExam[]> {
  try {
    const res = await request<Array<{
      exam_id: string;
      user_id: string;
      subject_id: string;
      title: string;
      exam_date: string;
      days_until_exam?: number;
      assessment_focus?: string;
    }>>('/api/exams/upcoming');
    if (Array.isArray(res)) {
      return res.map(e => ({
        examId: e.exam_id,
        userId: e.user_id,
        subjectId: e.subject_id,
        title: e.title,
        examDate: e.exam_date,
        daysUntilExam: e.days_until_exam,
        assessmentFocus: e.assessment_focus,
      }));
    }
  } catch {
    // empty state
  }
  return [];
}

export async function scheduleBackendExam(payload: {
  subjectId: string;
  title: string;
  examDate: string;
  courseId?: string;
}): Promise<BackendUpcomingExam | null> {
  try {
    const isoDate = payload.examDate.includes('T') ? payload.examDate : `${payload.examDate}T09:00:00`;
    const res = await request<{
      exam_id: string;
      user_id: string;
      subject_id: string;
      title: string;
      exam_date: string;
      days_until_exam?: number;
      assessment_focus?: string;
    }>('/api/exams', {
      method: 'POST',
      body: JSON.stringify({
        subject_id: payload.subjectId,
        course_id: payload.courseId,
        title: payload.title,
        exam_date: isoDate,
      }),
    });
    return {
      examId: res.exam_id,
      userId: res.user_id,
      subjectId: res.subject_id,
      title: res.title,
      examDate: res.exam_date,
      daysUntilExam: res.days_until_exam,
      assessmentFocus: res.assessment_focus,
    };
  } catch {
    return null;
  }
}

export interface QuizAttemptRecord {
  attemptId: string;
  quizId: string;
  title: string;
  subject: string;
  score: number;
  total: number;
  percentage: number;
  completedAt: string | null;
}

export async function fetchQuizAttempts(): Promise<QuizAttemptRecord[]> {
  try {
    const res = await request<Array<{
      attempt_id: string;
      quiz_id: string;
      title: string;
      subject: string;
      score: number;
      total: number;
      percentage: number;
      completed_at: string | null;
    }>>('/api/quizzes/attempts');
    if (Array.isArray(res)) {
      return res.map(r => ({
        attemptId: r.attempt_id,
        quizId: r.quiz_id,
        title: r.title,
        subject: r.subject,
        score: r.score,
        total: r.total,
        percentage: r.percentage,
        completedAt: r.completed_at,
      }));
    }
  } catch {
    // empty state
  }
  return [];
}

export interface QuizGenerationRequest {
  documentId?: string;
  courseId?: string;
  subjectId?: string;
  topic?: string;
  difficulty?: string;
  count?: number;
  sourceType?: 'Topic' | 'Subject' | 'Knowledge' | 'Notes' | 'Weak Topics';
  isExam?: boolean;
  questionCount?: number;
  subject?: string;
}

export interface GeneratedQuestion {
  id: string;
  text: string;
  options: string[];
  answer: number;
  explanation: string;
  topic?: string;
  difficulty?: string;
}

export interface GeneratedQuizResponse {
  id: string;
  title: string;
  source: string;
  subject: string;
  questions: GeneratedQuestion[];
  isDemo?: boolean;
}

export async function generateQuiz(req: QuizGenerationRequest): Promise<GeneratedQuizResponse> {
  const subjectId = req.subjectId || req.subject?.toLowerCase().replace(/\s+/g, '_') || 'operating_systems';
  const topicId = req.topic || 'General';
  const count = req.count || req.questionCount || 5;
  const diffLower = req.difficulty ? req.difficulty.toLowerCase() : 'medium';
  const backendDiff = ['easy', 'medium', 'hard'].includes(diffLower) ? diffLower : undefined;

  let res: {
    quiz_id?: string;
    title?: string;
    status?: string;
    message?: string;
    questions?: Array<{
      question_id: string;
      question_text: string;
      topic_id?: string;
      difficulty?: string;
      options: string[];
      explanation?: string;
      correct_answer?: string;
      source_chunk_id?: string;
    }>;
  };

  try {
    res = await request('/api/quizzes', {
      method: 'POST',
      body: JSON.stringify({
        subject_id: subjectId,
        course_id: req.courseId,
        document_id: req.documentId,
        topic_ids: req.topic ? [req.topic] : [topicId],
        difficulty: backendDiff,
        count: count,
        source_type: req.sourceType,
        title: req.topic ? `${req.topic} — ${req.isExam ? 'Timed Assessment' : 'Practice Quiz'}` : undefined,
      }),
    });
  } catch (err: any) {
    const rawMsg = err.message || '';
    try {
      const parsed = JSON.parse(rawMsg);
      if (parsed.detail) {
        throw new Error(parsed.detail);
      }
    } catch {
      // not json
    }
    throw err;
  }

  if (res.status === 'insufficient_material') {
    throw new Error(res.message || 'Insufficient study material found for the selected document. Please upload more study material.');
  }

  if (!res?.quiz_id || !res.questions || res.questions.length === 0) {
    throw new Error('Quiz generation returned no questions. Please try again.');
  }

  return {
    id: res.quiz_id,
    title: res.title || `${req.topic || 'Practice'} — Practice Quiz`,
    source: req.topic || 'Document Material',
    subject: req.subject || req.subjectId || 'Computer Science',
    questions: res.questions.map(q => {
      let answerIndex = 0;
      if (q.correct_answer && Array.isArray(q.options)) {
        const caClean = q.correct_answer.trim().toLowerCase();
        const foundIdx = q.options.findIndex(opt => {
          const optClean = opt.trim().toLowerCase();
          return (
            optClean === caClean ||
            (caClean.length >= 2 && optClean.startsWith(caClean.slice(0, 2))) ||
            (optClean.length >= 2 && caClean.startsWith(optClean.slice(0, 2))) ||
            (caClean.length > 3 && optClean.includes(caClean)) ||
            (optClean.length > 3 && caClean.includes(optClean))
          );
        });
        if (foundIdx !== -1) {
          answerIndex = foundIdx;
        }
      }
      return {
        id: q.question_id,
        text: q.question_text,
        options: q.options || [],
        answer: answerIndex,
        explanation: q.explanation || '',
        topic: q.topic_id || req.topic || 'General',
        difficulty: q.difficulty || 'medium',
      };
    }),
    isDemo: false,
  };
}

export interface QuizSubmissionResult {
  attemptId: string;
  quizId: string;
  score: number;
  total: number;
  percentage: number;
  weakTopics: Array<{ topicId: string; topic: string; mastery: number }>;
  strongTopics?: Array<{ topicId: string; topic: string; mastery: number }>;
  isDemo?: boolean;
}

export async function submitQuiz(
  quizId: string,
  answers: Array<{ questionId: string; selectedAnswer: string; timeTaken?: number }>
): Promise<QuizSubmissionResult> {
  const res = await request<{
    attempt_id: string;
    quiz_id: string;
    score: number;
    total: number;
    percentage: number;
    weak_topics: Array<{ topic_id: string; topic: string; mastery: number }>;
    strong_topics?: Array<{ topic_id: string; topic: string; mastery: number }>;
  }>(`/api/quizzes/${encodeURIComponent(quizId)}/submit`, {
    method: 'POST',
    body: JSON.stringify({
      answers: answers.map(a => ({
        question_id: a.questionId,
        selected_answer: a.selectedAnswer,
        time_taken: a.timeTaken || 0.0,
      })),
    }),
  });

  return {
    attemptId: res.attempt_id,
    quizId: res.quiz_id,
    score: res.score,
    total: res.total,
    percentage: res.percentage,
    weakTopics: (res.weak_topics || []).map(w => ({
      topicId: w.topic_id,
      topic: w.topic,
      mastery: w.mastery,
    })),
    strongTopics: (res.strong_topics || []).map(s => ({
      topicId: s.topic_id,
      topic: s.topic,
      mastery: s.mastery,
    })),
    isDemo: false,
  };
}

// Person 4: Study Planner and Tasks Endpoints (/api/plans, /api/plans/today, /api/tasks/{task_id})
export interface BackendStudyTask {
  task_id: string;
  study_plan_id?: string;
  user_id: string;
  course_id?: string;
  subject_id?: string;
  topic_id?: string;
  title: string;
  description?: string;
  scheduled_date: string;
  start_time?: string;
  duration_minutes: number;
  priority: string;
  status: string;
}

export interface BackendTodayPlan {
  date: string;
  user_id: string;
  total_tasks: number;
  total_scheduled_minutes: number;
  completed_minutes: number;
  tasks: BackendStudyTask[];
  isDemo?: boolean;
}

export async function fetchTodayPlan(): Promise<BackendTodayPlan | null> {
  try {
    const res = await request<BackendTodayPlan>('/api/plans/today');
    return { ...res, isDemo: false };
  } catch {
    return null;
  }
}

export async function fetchStudyPlans(): Promise<any[] | null> {
  try {
    return await request<any[]>('/api/plans');
  } catch {
    return null;
  }
}

export async function createStudyPlan(payload: {
  startDate: string;
  endDate: string;
  availableMinutesPerDay?: number;
  userId?: string;
}): Promise<any | null> {
  try {
    const cachedUser = localStorage.getItem('acadassist.auth.user');
    const parsedUser = cachedUser ? JSON.parse(cachedUser) : null;
    const uid = payload.userId || parsedUser?.id || 'student';
    return await request('/api/plans', {
      method: 'POST',
      body: JSON.stringify({
        user_id: uid,
        start_date: payload.startDate,
        end_date: payload.endDate,
        available_minutes_per_day: payload.availableMinutesPerDay || 120,
      }),
    });
  } catch {
    return null;
  }
}

export async function updateTaskStatus(
  taskId: string,
  status: 'pending' | 'in_progress' | 'completed' | 'skipped',
  rescheduledDate?: string,
  rescheduledTime?: string
): Promise<BackendStudyTask | null> {
  try {
    return await request<BackendStudyTask>(
      `/api/tasks/${encodeURIComponent(taskId)}`,
      {
        method: 'PATCH',
        body: JSON.stringify({
          status,
          rescheduled_date: rescheduledDate,
          rescheduled_time: rescheduledTime,
        }),
      }
    );
  } catch {
    return null;
  }
}

// Notes API (/api/notes)
export interface BackendNote {
  id: string;
  user_id: string;
  document_id?: string;
  title: string;
  content: string;
  subject?: string;
  note_type: string;
  created_at: string;
  updated_at: string;
}

export async function fetchNotes(): Promise<BackendNote[]> {
  try {
    return await request<BackendNote[]>('/api/notes');
  } catch {
    return [];
  }
}

export async function createNote(payload: {
  title: string;
  content: string;
  subject?: string;
  note_type?: string;
  document_id?: string;
}): Promise<BackendNote | null> {
  try {
    return await request<BackendNote>('/api/notes', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  } catch {
    return null;
  }
}

export async function updateNote(
  noteId: string,
  payload: { title?: string; content?: string; subject?: string; note_type?: string }
): Promise<BackendNote | null> {
  try {
    return await request<BackendNote>(`/api/notes/${encodeURIComponent(noteId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  } catch {
    return null;
  }
}

export async function deleteNote(noteId: string): Promise<boolean> {
  try {
    await request(`/api/notes/${encodeURIComponent(noteId)}`, { method: 'DELETE' });
    return true;
  } catch {
    return false;
  }
}

// Chat API (/api/chat)
export interface BackendChatMessage {
  id: string;
  role: string;
  text: string;
  time: string;
}

export async function fetchChatHistory(): Promise<BackendChatMessage[]> {
  try {
    return await request<BackendChatMessage[]>('/api/chat/history');
  } catch {
    return [];
  }
}

export async function appendChatMessage(role: string, text: string): Promise<BackendChatMessage | null> {
  try {
    return await request<BackendChatMessage>('/api/chat/message', {
      method: 'POST',
      body: JSON.stringify({ role, text }),
    });
  } catch {
    return null;
  }
}

export async function clearBackendChatHistory(): Promise<void> {
  try {
    await request('/api/chat/history', { method: 'DELETE' });
  } catch {
    /* ignore */
  }
}

export async function chatWithAssistant(
  message: string,
  context?: { materialId?: string; subject?: string; courseId?: string; subjectId?: string }
): Promise<ChatResult> {
  return sendChatMessage(message, context?.materialId, {
    courseId: context?.courseId,
    subjectId: context?.subjectId || context?.subject,
  });
}

export { API_BASE };
