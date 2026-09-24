import { useEffect, useMemo, useState, type ChangeEvent } from 'react';
import {
  Download, Edit3, Eye, FileText, FileQuestion, MoreHorizontal, Plus, Search,
  Sparkles, Trash2, UploadCloud, BookOpen, Star, MessageSquare, Database, CheckCircle2
} from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useApp, type Note } from '../context/AppContext';
import Modal from '../components/ui/Modal';
import { deleteFile, getFile, saveFile } from '../services/fileStore';
import { uploadDocument, downloadDocument, displayDocumentStatus, isDocumentReady, formatApiError } from '../services/api';

type Material = ReturnType<typeof useApp>['knowledgeMaterials'][number];


export default function Knowledge() {
  const {
    knowledgeMaterials, addKnowledgeMaterial, updateKnowledgeMaterial, deleteKnowledgeMaterial,
    notes, addNote, updateNote, deleteNote, pushToast, subjects, quizzes, courses
  } = useApp();
  const [params] = useSearchParams();
  const navigate = useNavigate();

  const [q, setQ] = useState(params.get('q') || '');
  const [tab, setTab] = useState<'Documents' | 'Notes'>('Documents');
  const [subject, setSubject] = useState('All');
  const [type, setType] = useState('All');
  const [sort, setSort] = useState('Newest');

  const [uploadOpen, setUploadOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  const [uploadSubject, setUploadSubject] = useState(subjects[0]?.id || subjects[0]?.name || 'cn');
  const [uploadCourse, setUploadCourse] = useState(courses[0]?.id || subjects[0]?.id || 'cn');
  const [actions, setActions] = useState<string | null>(null);

  const [preview, setPreview] = useState<Material | null>(null);
  const [previewNote, setPreviewNote] = useState<Note | null>(null);
  const [editDoc, setEditDoc] = useState<Material | null>(null);
  const [editNote, setEditNote] = useState<Note | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Material | null>(null);
  const [busy, setBusy] = useState(false);

  const docs = useMemo(
    () =>
      knowledgeMaterials
        .filter(
          m =>
            (subject === 'All' || m.subject === subject) &&
            (type === 'All' || m.type === type) &&
            `${m.name} ${m.subject}`.toLowerCase().includes(q.toLowerCase())
        )
        .sort((a, b) =>
          sort === 'Name'
            ? a.name.localeCompare(b.name)
            : new Date(b.addedOn).getTime() - new Date(a.addedOn).getTime()
        ),
    [knowledgeMaterials, q, subject, type, sort]
  );

  const noteList = useMemo(
    () =>
      notes
        .filter(
          n =>
            (subject === 'All' || n.subject === subject) &&
            `${n.title} ${n.content} ${n.source}`.toLowerCase().includes(q.toLowerCase())
        )
        .sort((a, b) => (sort === 'Name' ? a.title.localeCompare(b.title) : b.id.localeCompare(a.id))),
    [notes, q, subject, sort]
  );

  const processedCount = knowledgeMaterials.filter(
    m => m.status === 'Stored Locally · Ready for Processing' || m.status === 'Ready'
  ).length;

  const onFile = (f: File | null) => {
    if (!f) return;
    if (f.size > 50 * 1024 * 1024) {
      pushToast('Maximum file size is 50 MB', 'error');
      return;
    }
    const ext = f.name.split('.').pop()?.toLowerCase();
    if (!['pdf', 'docx', 'pptx', 'txt'].includes(ext || '')) {
      pushToast('Supported formats: PDF, DOCX, PPTX and TXT', 'error');
      return;
    }
    setFile(f);
    const initialSub = subjects[0];
    setUploadSubject(initialSub?.id || initialSub?.name || 'cn');
    setUploadCourse(courses[0]?.id || initialSub?.id || 'cn');
    setUploadOpen(true);
  };

  const createUpload = async () => {
    if (!file || !uploadSubject) {
      pushToast('Select a subject first', 'error');
      return;
    }
    setBusy(true);
    try {
      const selectedSub = subjects.find(s => s.id === uploadSubject || s.name === uploadSubject) || subjects[0];
      const selectedCourse = courses.find(c => c.id === uploadCourse || c.id === selectedSub?.id || c.name === selectedSub?.name) || courses[0];
      const courseId = selectedCourse?.id || selectedSub?.id || 'cn';
      const subjectId = selectedSub?.id || 'cn';

      const uploadRes = await uploadDocument(file, courseId, subjectId);
      const ext = file.name.split('.').pop()?.toLowerCase();
      const material = {
        id: uploadRes.id,
        name: file.name,
        subject: selectedSub?.name || uploadSubject,
        type: (ext === 'pptx' ? 'PPT' : ext?.toUpperCase()) as Material['type'],
        size: `${(file.size / 1024 / 1024).toFixed(1)} MB`,
        addedOn: new Date().toISOString(),
        status: displayDocumentStatus(uploadRes.status),
        rawStatus: uploadRes.status,
        starred: false,
      };
      addKnowledgeMaterial(material);
      saveFile(uploadRes.id, file).catch(() => {});
      if (ext === 'txt') {
        const text = await file.text();
        addNote({
          id: crypto.randomUUID(),
          title: `${file.name.replace(/\.[^.]+$/, '')} — Summary`,
          subject: selectedSub?.name || uploadSubject,
          source: file.name,
          type: 'Summary',
          content: text.slice(0, 3500),
          createdAt: 'Just now',
        });
      }
      setFile(null);
      setUploadOpen(false);
      if (isDocumentReady(material.rawStatus)) {
        pushToast('Material uploaded and processed securely');
      } else {
        pushToast(
          `Uploaded, but processing didn't finish (${displayDocumentStatus(uploadRes.status)}). It may not be usable for quizzes yet.`,
          'error'
        );
      }
    } catch (e) {
      console.error('Failed to upload file:', e);
      pushToast(formatApiError(e, 'Something went wrong while processing this document. Please try again.'), 'error');
    } finally {
      setBusy(false);
    }
  };

  const download = async (m: Material) => {
    try {
      if (m.id) {
        await downloadDocument(m.id, m.name);
        pushToast('Download started');
        return;
      }
      const blob = await getFile(m.name);
      if (!blob) throw new Error('Original file is not available');
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = m.name;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      pushToast('Download started');
    } catch (e) {
      pushToast(e instanceof Error ? e.message : 'Download failed', 'error');
    }
  };


  const openPreview = async (m: Material) => {
    setPreview(m);
  };

  const askAi = (m: Material) => {
    if (!m.id || !m.id.trim()) {
      pushToast('Cannot Ask AI: Document ID is missing', 'error');
      return;
    }
    navigate(`/assistant?materialId=${encodeURIComponent(m.id)}&subject=${encodeURIComponent(m.subject)}`);
  };

  const generate = (m: Material, kind: 'Summary' | 'AI Notes' | 'Exam Notes' | 'Easy Explanation') => {
    const clean = m.name.replace(/\.[^.]+$/, '');
    const templates: { [K in typeof kind]: string } = {
      Summary: `${clean} — Concise Curriculum Summary\n\n• Core Concepts: Definitional outline and mechanism.\n• Formulas & Theorems: Exact mathematical bounds and properties.\n• Edge Cases: Common edge cases and exam tricks.\n• Key Diagrams: Process interaction and flow.`,
      'AI Notes': `${clean} — Comprehensive Exam Notes\n\n1. Foundational Theory\n2. Detailed Step-by-Step Mechanisms\n3. Proofs / Derivations\n4. Comparative Analysis (Trade-offs)\n5. High-Frequency Exam Questions with Explanations`,
      'Exam Notes': `${clean} — High-Yield Exam Notes\n\nSummary for rapid revision before exams.\n\n• Necessary conditions and criteria.\n• Step-by-step algorithms.\n• Complexity summary (Time & Space).`,
      'Easy Explanation': `${clean} — Intuitive Explanation\n\nSimple explanation starting with an everyday analogy, walking through the core technical mechanism, and contrasting with common misconceptions.`,
    };
    addNote({
      id: crypto.randomUUID(),
      title: `${clean} — ${kind}`,
      subject: m.subject,
      source: m.name,
      type: kind,
      content: templates[kind],
      createdAt: 'Just now',
    });
    pushToast(`${kind} created`);
    setActions(null);
  };

  const removeDoc = async () => {
    if (!deleteTarget) return;
    deleteKnowledgeMaterial(deleteTarget.id || deleteTarget.name);
    await deleteFile(deleteTarget.id || deleteTarget.name);
    setDeleteTarget(null);
    pushToast('Document deleted', 'info');
  };

  return (
    <div className="page-stack">
      {/* Hero Header */}
      <div className="page-hero">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="eyebrow">YOUR KNOWLEDGE BASE</span>
            <span className="soft-badge" style={{ fontSize: '0.62rem', padding: '2px 8px' }}>
              Azure Storage Ready
            </span>
          </div>
          <h1>Everything you study, organized.</h1>
          <p>
            Store materials by subject, preview documents, download originals, and generate exam notes or quizzes.
          </p>
        </div>
        <button className="btn primary" onClick={() => setUploadOpen(true)}>
          <UploadCloud size={16} /> Upload material
        </button>
      </div>

      {/* Library Status Metrics Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="card p-3.5 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[var(--color-green-light)] text-[var(--color-green-accent)] flex items-center justify-center flex-shrink-0">
            <FileText size={18} />
          </div>
          <div>
            <span className="text-lg font-bold text-[var(--color-text-dark)] leading-none block">
              {knowledgeMaterials.length}
            </span>
            <small className="text-[.65rem] text-[var(--color-text-muted)]">Total Study Materials</small>
          </div>
        </div>

        <div className="card p-3.5 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center flex-shrink-0">
            <CheckCircle2 size={18} />
          </div>
          <div>
            <span className="text-lg font-bold text-[var(--color-text-dark)] leading-none block">
              {processedCount}
            </span>
            <small className="text-[.65rem] text-[var(--color-text-muted)]">Stored Locally · Ready for Processing</small>
          </div>
        </div>

        <div className="card p-3.5 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 flex items-center justify-center flex-shrink-0">
            <BookOpen size={18} />
          </div>
          <div>
            <span className="text-lg font-bold text-[var(--color-text-dark)] leading-none block">
              {notes.length}
            </span>
            <small className="text-[.65rem] text-[var(--color-text-muted)]">AI Notes Generated</small>
          </div>
        </div>

        <div className="card p-3.5 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 flex items-center justify-center flex-shrink-0">
            <Database size={18} />
          </div>
          <div>
            <span className="text-xs font-bold text-[var(--color-text-dark)] leading-tight block">
              Local Browser Cache
            </span>
            <small className="text-[.62rem] text-[var(--color-text-muted)]">Ready for Azure Blob Sync</small>
          </div>
        </div>
      </div>

      {/* Upload Drop Zone */}
      <div
        className={`upload-zone ${drag ? 'dragging' : ''}`}
        onDragOver={e => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={e => {
          e.preventDefault();
          setDrag(false);
          onFile(e.dataTransfer.files[0]);
        }}
      >
        <UploadCloud size={28} />
        <h3>Drop course study material here</h3>
        <p>PDF · DOCX · PPTX · TXT · up to 50 MB per file</p>
        <label className="btn secondary">
          <Plus size={15} /> Browse files
          <input
            hidden
            type="file"
            accept=".pdf,.docx,.pptx,.txt"
            onChange={(e: ChangeEvent<HTMLInputElement>) => onFile(e.target.files?.[0] || null)}
          />
        </label>
      </div>

      {/* Tabs */}
      <div className="tabs-row">
        <button className={tab === 'Documents' ? 'active' : ''} onClick={() => setTab('Documents')}>
          Documents ({knowledgeMaterials.length})
        </button>
        <button className={tab === 'Notes' ? 'active' : ''} onClick={() => setTab('Notes')}>
          AI Notes ({notes.length})
        </button>
        <button onClick={() => navigate('/assessment')}>
          <FileQuestion size={15} /> Quizzes ({quizzes.length})
        </button>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="toolbar">
        <div className="search-box">
          <Search size={16} />
          <input
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="Search documents, notes or subjects..."
          />
        </div>
        <select className="select" value={subject} onChange={e => setSubject(e.target.value)}>
          <option>All</option>
          {subjects.map(s => (
            <option key={s.id}>{s.name}</option>
          ))}
        </select>
        {tab === 'Documents' && (
          <select className="select" value={type} onChange={e => setType(e.target.value)}>
            <option>All</option>
            <option>PDF</option>
            <option>DOCX</option>
            <option>PPT</option>
            <option>TXT</option>
          </select>
        )}
        <select className="select" value={sort} onChange={e => setSort(e.target.value)}>
          <option>Newest</option>
          <option>Name</option>
        </select>
      </div>

      {/* Documents Grid */}
      {tab === 'Documents' ? (
        <div className="doc-grid">
          {docs.map(m => (
            <div className="doc-card" key={m.id || m.name}>
              <div className="doc-top">
                <div className="doc-icon">
                  <FileText size={20} />
                </div>
                <button
                  className="icon-button"
                  onClick={() => setActions(actions === (m.id || m.name) ? null : m.id || m.name)}
                  aria-label="Document options"
                >
                  <MoreHorizontal size={18} />
                </button>
                {actions === (m.id || m.name) && (
                  <div className="action-menu">
                    <button
                      onClick={() => {
                        openPreview(m);
                        setActions(null);
                      }}
                    >
                      <Eye size={14} /> Preview
                    </button>
                    <button
                      onClick={() => {
                        askAi(m);
                        setActions(null);
                      }}
                    >
                      <MessageSquare size={14} /> Ask AI
                    </button>
                    <button
                      onClick={() => {
                        setEditDoc(m);
                        setActions(null);
                      }}
                    >
                      <Edit3 size={14} /> Edit details
                    </button>
                    <button onClick={() => generate(m, 'Summary')}>
                      <Sparkles size={14} /> AI Summary
                    </button>
                    <button onClick={() => generate(m, 'AI Notes')}>
                      <BookOpen size={14} /> Exam Notes
                    </button>
                    <button
                      onClick={() => {
                        navigate(`/assessment?source=document&material=${encodeURIComponent(m.name)}`);
                        setActions(null);
                      }}
                    >
                      <FileQuestion size={14} /> Generate Quiz
                    </button>
                    <button onClick={() => download(m)}>
                      <Download size={14} /> Download
                    </button>
                    <button
                      onClick={() => {
                        setDeleteTarget(m);
                        setActions(null);
                      }}
                      className="danger"
                    >
                      <Trash2 size={14} /> Delete
                    </button>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between mt-2.5 mb-1">
                <span className="doc-type">{m.type}</span>
                {/* Visual Document Lifecycle (Task 9) */}
                {m.rawStatus === 'processed' ? (
                  <div className="flex items-center gap-1 text-[0.62rem] font-bold text-emerald-700 dark:text-emerald-400" title="Uploaded, processed, and indexed for search and quizzes">
                    <span>✓ Uploaded</span>
                    <span>·</span>
                    <span>✓ Processed</span>
                    <span>·</span>
                    <span>✓ Indexed</span>
                  </div>
                ) : m.rawStatus === 'processing' ? (
                  <div className="flex items-center gap-1 text-[0.62rem] font-bold text-amber-600 dark:text-amber-400" title="Document is currently being processed and indexed">
                    <span>✓ Uploaded</span>
                    <span>·</span>
                    <span className="animate-pulse">⏳ Processing…</span>
                  </div>
                ) : m.rawStatus === 'failed' ? (
                  <div className="flex items-center gap-1 text-[0.62rem] font-bold text-red-600 dark:text-red-400" title="Processing error occurred">
                    <span>✓ Uploaded</span>
                    <span>·</span>
                    <span>⚠️ Processing failed</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-1 text-[0.62rem] font-bold text-blue-600 dark:text-blue-400" title="Document uploaded and stored; ready for processing">
                    <span>✓ Uploaded</span>
                    <span>·</span>
                    <span>⏳ Ready to Process</span>
                  </div>
                )}
              </div>

              <h3 className="line-clamp-2">{m.name}</h3>
              <p>
                {m.subject} · {m.size}
              </p>

              {/* Document Action Buttons: [Ask AI], [Quiz], [Preview] (Task 9) */}
              <div className="doc-actions pt-2.5 border-t border-[var(--color-border-light)] mt-2.5">
                <button
                  className="btn primary text-xs"
                  onClick={() => askAi(m)}
                  disabled={!m.id}
                  title={m.id ? 'Query AI with this document context' : 'Cannot Ask AI: Document ID is missing'}
                >
                  <MessageSquare size={13} /> Ask AI
                </button>
                <button
                  className="btn secondary text-xs"
                  onClick={() => {
                    navigate(`/assessment?source=document&material=${encodeURIComponent(m.name)}&document_id=${encodeURIComponent(m.id || '')}`);
                  }}
                  disabled={m.rawStatus === 'failed'}
                  title="Generate assessment from this document"
                >
                  <FileQuestion size={13} /> Quiz
                </button>
                <button className="btn subtle text-xs" onClick={() => openPreview(m)}>
                  <Eye size={13} /> Preview
                </button>
                <button
                  className="icon-button ml-auto"
                  onClick={() => updateKnowledgeMaterial(m.id || m.name, { starred: !m.starred })}
                  aria-label="Star document"
                >
                  <Star size={14} fill={m.starred ? 'currentColor' : 'none'} />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Notes Grid */
        <div className="note-grid">
          {noteList.map(n => (
            <div className="note-card" key={n.id}>
              <div className="doc-top">
                <div className="note-icon">
                  <BookOpen size={18} />
                </div>
                <button className="icon-button" onClick={() => setEditNote(n)} aria-label="Edit note">
                  <Edit3 size={15} />
                </button>
              </div>
              <span className="soft-badge">{n.type}</span>
              <h3 className="line-clamp-1">{n.title}</h3>
              <p className="line-clamp-3">{n.content}</p>
              <small>
                {n.subject} · {n.source}
              </small>
              <div className="doc-actions">
                <button className="btn secondary text-xs" onClick={() => setPreviewNote(n)}>
                  <Eye size={13} /> Read
                </button>
                <button
                  className="btn subtle text-xs"
                  onClick={() =>
                    navigate(`/assessment?source=notes&material=${encodeURIComponent(n.title)}`)
                  }
                >
                  <FileQuestion size={13} /> Quiz me
                </button>
                <button
                  className="icon-button danger ml-auto"
                  onClick={() => deleteNote(n.id)}
                  aria-label="Delete note"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State (Task 4) */}
      {tab === 'Documents' && docs.length === 0 && (
        <div className="empty-state py-10">
          {knowledgeMaterials.length === 0 ? (
            <>
              <div className="text-3xl mb-2">📚</div>
              <h3 className="text-base font-bold text-[var(--color-text-dark)]">No study material yet</h3>
              <p className="text-xs text-[var(--color-text-muted)] max-w-sm mx-auto mt-1 mb-4">
                Upload your notes or PDF to start building your knowledge base.
              </p>
              <button className="btn primary" onClick={() => setUploadOpen(true)}>
                <UploadCloud size={15} /> Upload Document
              </button>
            </>
          ) : (
            <>
              <div className="text-3xl mb-2">🔎</div>
              <h3 className="text-base font-bold text-[var(--color-text-dark)]">No matching study material found</h3>
              <p className="text-xs text-[var(--color-text-muted)] max-w-sm mx-auto mt-1 mb-4">
                Try changing your search keywords or clearing active filters to find your study documents.
              </p>
              <button
                className="btn secondary text-xs"
                onClick={() => {
                  setQ('');
                  setSubject('All');
                  setType('All');
                }}
              >
                Clear Filters
              </button>
            </>
          )}
        </div>
      )}

      {tab === 'Notes' && noteList.length === 0 && (
        <div className="empty-state py-10">
          <div className="text-3xl mb-2">📝</div>
          <h3 className="text-base font-bold text-[var(--color-text-dark)]">No notes available yet</h3>
          <p className="text-xs text-[var(--color-text-muted)] max-w-sm mx-auto mt-1 mb-4">
            Generate high-yield notes using AI or create your own study notes.
          </p>
        </div>
      )}

      {/* Upload Modal */}
      <Modal
        open={uploadOpen}
        onClose={() => !busy && setUploadOpen(false)}
        title="Add study material"
        subtitle="Stored in local browser cache. Ready to synchronize with Azure Blob Storage upon backend connection."
      >
        {file ? (
          <>
            <div className="file-preview">
              <FileText size={20} />
              <span>
                <b>{file.name}</b>
                <br />
                {(file.size / 1024 / 1024).toFixed(1)} MB
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', margin: '1rem 0' }}>
              <label>
                Subject
                <select
                  className="select full"
                  value={uploadSubject}
                  onChange={e => {
                    const subId = e.target.value;
                    setUploadSubject(subId);
                    const matchingCourse = courses.find(c => c.id === subId);
                    if (matchingCourse) {
                      setUploadCourse(matchingCourse.id);
                    }
                  }}
                >
                  {subjects.map(s => (
                    <option key={s.id} value={s.id}>{s.name} ({s.code || s.tag})</option>
                  ))}
                </select>
              </label>
              <label>
                Course
                <select
                  className="select full"
                  value={uploadCourse}
                  onChange={e => setUploadCourse(e.target.value)}
                >
                  {courses.map(c => (
                    <option key={c.id} value={c.id}>{c.name} ({c.code})</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="modal-actions">
              <button className="btn secondary" disabled={busy} onClick={() => setFile(null)}>
                Choose another
              </button>
              <button className="btn primary" disabled={busy} onClick={createUpload}>
                {busy ? 'Saving…' : 'Upload & add'}
              </button>
            </div>
          </>
        ) : (
          <label className="big-drop">
            <UploadCloud size={30} />
            <span>Select PDF, DOCX, PPTX or TXT</span>
            <input
              type="file"
              accept=".pdf,.docx,.pptx,.txt"
              onChange={e => onFile(e.target.files?.[0] || null)}
            />
          </label>
        )}
      </Modal>

      {/* Document Preview Modal */}
      <Modal
        open={!!preview}
        onClose={() => setPreview(null)}
        title={preview?.name || 'Document'}
        subtitle={preview ? `${preview.subject} · ${preview.type} · ${preview.size}` : ''}
        wide
      >
        {preview && <DocumentPreview material={preview} />}
        {preview && (
          <div className="modal-actions">
            <button
              className="btn secondary"
              onClick={() => askAi(preview)}
              disabled={!preview.id}
              title={preview.id ? "Ask AI about this document" : "Cannot Ask AI: Document ID is missing"}
            >
              <MessageSquare size={14} /> Ask AI about this document
            </button>
            <button className="btn secondary" onClick={() => download(preview)}>
              <Download size={14} /> Download original
            </button>
            <button
              className="btn primary"
              onClick={() => {
                navigate(`/assessment?source=document&material=${encodeURIComponent(preview.name)}`);
                setPreview(null);
              }}
            >
              <FileQuestion size={14} /> Generate quiz
            </button>
          </div>
        )}
      </Modal>

      {/* Note Preview Modal */}
      <Modal
        open={!!previewNote}
        onClose={() => setPreviewNote(null)}
        title={previewNote?.title || 'Note'}
        subtitle={previewNote ? `${previewNote.subject} · ${previewNote.type}` : ''}
        wide
      >
        {previewNote && <div className="preview-paper">{previewNote.content}</div>}
      </Modal>

      {/* Edit Document Modal */}
      <Modal open={!!editDoc} onClose={() => setEditDoc(null)} title="Edit document details">
        <EditDocument
          material={editDoc}
          subjects={subjects.map(s => s.name)}
          onSave={patch => {
            if (editDoc) {
              updateKnowledgeMaterial(editDoc.id || editDoc.name, patch);
              setEditDoc(null);
              pushToast('Document details updated');
            }
          }}
        />
      </Modal>

      {/* Edit Note Modal */}
      <Modal open={!!editNote} onClose={() => setEditNote(null)} title="Edit note">
        <EditNote
          note={editNote}
          onSave={patch => {
            if (editNote) {
              updateNote(editNote.id, patch);
              setEditNote(null);
              pushToast('Note updated');
            }
          }}
        />
      </Modal>

      {/* Delete Document Modal */}
      <Modal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete document"
        subtitle="This removes the document from this browser's Knowledge library."
      >
        <p className="text-sm">
          Delete <b>{deleteTarget?.name}</b>? AI notes created from it will remain available.
        </p>
        <div className="modal-actions">
          <button className="btn secondary" onClick={() => setDeleteTarget(null)}>
            Cancel
          </button>
          <button className="btn danger" onClick={removeDoc}>
            <Trash2 size={14} /> Delete
          </button>
        </div>
      </Modal>
    </div>
  );
}

function DocumentPreview({ material }: { material: Material }) {
  const [url, setUrl] = useState<string | null>(null);
  const [text, setText] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    let objectUrl: string | undefined;

    getFile(material.id || material.name)
      .then(async blob => {
        if (!active) return;
        if (!blob) {
          setError(
            'Original file is stored as a curriculum reference in this demo workspace. When a real file is uploaded, the preview will render in-browser.'
          );
          setUrl(null);
          setText('');
          return;
        }
        if (material.type === 'TXT') {
          const content = await blob.text();
          if (active) {
            setText(content);
            setUrl(null);
            setError('');
          }
          return;
        }
        objectUrl = URL.createObjectURL(blob);
        if (active) {
          setUrl(objectUrl);
          setText('');
          setError('');
        }
      })
      .catch(e => {
        if (active) {
          setError(e instanceof Error ? e.message : 'Could not open file');
          setUrl(null);
          setText('');
        }
      });

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [material]);

  if (error)
    return (
      <div className="preview-paper">
        <b>{material.name}</b>
        <p className="text-xs text-[var(--color-text-muted)] mt-2">{error}</p>
        <div className="mt-3 p-3 rounded-lg bg-[var(--color-green-light)] text-[var(--color-green-accent)] text-xs">
          <b>Metadata Available:</b> Subject: {material.subject} · File format: {material.type} · Size: {material.size} · Status: {material.status}
        </div>
      </div>
    );
  if (text) return <pre className="preview-paper">{text}</pre>;
  if (url && material.type === 'PDF')
    return (
      <iframe
        title={material.name}
        src={url}
        style={{ width: '100%', height: 520, border: 0, borderRadius: 12 }}
      />
    );

  return (
    <div className="preview-paper">
      <b>{material.name}</b>
      <p>
        This file format ({material.type}) is stored safely. Browser-native rendering is optimized for PDF and TXT. For DOCX/PPTX, please download to open in native viewers.
      </p>
    </div>
  );
}

function EditDocument({
  material,
  subjects,
  onSave,
}: {
  material: Material | null;
  subjects: string[];
  onSave: (p: Partial<Material>) => void;
}) {
  const [name, setName] = useState(material?.name || '');
  const [sub, setSub] = useState(material?.subject || subjects[0] || '');

  return (
    <>
      <label>
        Name
        <input className="input" value={name} onChange={e => setName(e.target.value)} />
      </label>
      <label>
        Subject
        <select className="select full" value={sub} onChange={e => setSub(e.target.value)}>
          {subjects.map(s => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <div className="modal-actions">
        <button className="btn secondary" onClick={() => onSave({})}>
          Cancel
        </button>
        <button
          className="btn primary"
          disabled={!name.trim()}
          onClick={() => onSave({ name: name.trim(), subject: sub })}
        >
          <Edit3 size={14} /> Save changes
        </button>
      </div>
    </>
  );
}

function EditNote({ note, onSave }: { note: Note | null; onSave: (p: Partial<Note>) => void }) {
  const [title, setTitle] = useState(note?.title || '');
  const [content, setContent] = useState(note?.content || '');

  return (
    <>
      <label>
        Title
        <input className="input" value={title} onChange={e => setTitle(e.target.value)} />
      </label>
      <label>
        Content
        <textarea
          className="textarea"
          rows={10}
          value={content}
          onChange={e => setContent(e.target.value)}
        />
      </label>
      <div className="modal-actions">
        <button
          className="btn primary"
          disabled={!title.trim()}
          onClick={() => onSave({ title: title.trim(), content })}
        >
          Save changes
        </button>
      </div>
    </>
  );
}
