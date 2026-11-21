import { useEffect, useRef, useState } from 'react';
import { Send, Mic, Sparkles, Trash2, Copy, Check, Info, Bot, Database } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import HeroHeader from '../components/ui/HeroHeader';
import SectionHeader from '../components/ui/SectionHeader';
import Modal from '../components/ui/Modal';
import { useApp } from '../context/AppContext';
import { chatWithAssistant, fetchDocuments, type DocumentUploadResponse } from '../services/api';

const QUICK = [
  ['💡 Explain Concept', 'Explain Deadlock Coffman conditions in simple language with an example'],
  ['📝 Summarize Material', 'Summarize key points and exam criteria for TCP vs UDP flow control'],
  ['📄 High-Yield Notes', 'Create exam-ready revision notes for B+ tree indexing'],
  ['⚖️ Compare Topics', 'Compare Deadlock Prevention vs Deadlock Avoidance'],
  ['🎯 Create Practice', 'Generate 5 conceptual questions on CPU scheduling algorithms'],
];

const PROMPTS = [
  'Explain paging and virtual-to-physical address translation',
  'What is the difference between TCP and UDP sliding window?',
  'Explain BCNF decomposition and why it avoids update anomalies',
  'How does Round Robin scheduling choose the time quantum?',
  'Walk through Binary Search complexity and midpoint overflow prevention',
];

export default function Assistant() {
  const { chatHistory, addChatMessage, clearChatHistory, pushToast } = useApp();
  const [params] = useSearchParams();

  const [input, setInput] = useState('');
  const [materialId, setMaterialId] = useState<string | null>(null);
  const [subject, setSubject] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentUploadResponse[]>([]);
  const [typing, setTyping] = useState(false);
  const [tool, setTool] = useState<string | null>(null);
  const [modelModal, setModelModal] = useState(false);
  const [recentModal, setRecentModal] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  const [modelName, setModelName] = useState('AcadAssist RAG Engine (Azure Foundry / Local Hybrid)');
  const [copied, setCopied] = useState<number | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const rawId = params.get('materialId');
    if (rawId && rawId.trim()) {
      setMaterialId(rawId.trim());
    }
    const rawSubject = params.get('subject');
    if (rawSubject) {
      setSubject(rawSubject);
    }
    const urlPrompt = params.get('prompt');
    if (urlPrompt) {
      setInput(urlPrompt);
    }
  }, [params]);

  useEffect(() => {
    fetchDocuments().then(docs => {
      if (docs && docs.length > 0) {
        setDocuments(docs);
        if (!params.get('materialId')) {
          setMaterialId(docs[0].id);
        }
      }
    }).catch(() => {});
  }, [params]);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, typing]);

  const send = async (text = input) => {
    const value = text.trim();
    if (!value || typing) return;
    setInput('');
    // POST /api/chat already persists both user and assistant messages in the database,
    // so pass skipBackendSave=true to avoid duplicate DB rows.
    addChatMessage('user', value, undefined, undefined, true);
    setTyping(true);
    try {
      const context = materialId ? { materialId, ...(subject ? { subject } : {}) } : (subject ? { subject } : undefined);
      const r = await chatWithAssistant(value, context);
      addChatMessage('assistant', r.text, r.sources, r.actions, true);
    } catch (e) {
      addChatMessage(
        'assistant',
        `Could not reach the AI service. ${e instanceof Error ? e.message : 'Please try again.'}`,
        undefined,
        undefined,
        true
      );
    } finally {
      setTyping(false);
    }
  };

  const selectTool = (label: string, prompt: string) => {
    setTool(label);
    setInput(prompt);
  };

  const voice = () => {
    const SpeechRecognition = (
      window as Window & {
        webkitSpeechRecognition?: new () => {
          lang: string;
          start: () => void;
          onresult: (e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void;
          onerror: () => void;
        };
      }
    ).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      pushToast('Voice input is not supported in this browser', 'error');
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.onresult = e => setInput(e.results[0][0].transcript);
    recognition.onerror = () => pushToast('Voice input failed', 'error');
    recognition.start();
    pushToast('Listening for voice prompt…', 'info');
  };

  const copy = (text: string, index: number) => {
    navigator.clipboard?.writeText(text).then(() => {
      setCopied(index);
      window.setTimeout(() => setCopied(null), 1200);
      pushToast('Response copied to clipboard');
    }).catch(() => pushToast('Clipboard copy unavailable', 'error'));
  };

  return (
    <div className="page-stack">
      <HeroHeader
        tag="AI STUDY ASSISTANT"
        title={
          <>
            Your Coursework <span className="accent">Study Companion.</span>
          </>
        }
        subtitle="Clarify doubts, explain course concepts, generate summaries, and prepare for upcoming exams with grounded citations."
      />

      {/* Integration Status Banner */}
      <div className="card p-3 flex items-center justify-between text-xs bg-[var(--color-green-light)] text-[var(--color-green-accent)] border-[var(--color-green-border)]">
        <div className="flex items-center gap-2">
          <Bot size={16} />
          <span>
            <b>Grounded RAG Pipeline Active:</b> Answers are grounded in your uploaded documents and course knowledge base with verified source citations.
          </span>
        </div>
        <span className="font-semibold text-[.65rem] px-2 py-0.5 rounded bg-white/60 dark:bg-black/20">
          Hybrid BM25 + Vector Search
        </span>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-6">
        {/* Left Chat Window */}
        <div>
          <div className="card mb-3 p-0">
            {/* Chat Header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--color-card-border)]">
              <div>
                <b className="text-sm">AcadAssist AI</b>
                <span className="ml-2 text-[.65rem] text-green-600 font-semibold">
                  ● {modelName}
                </span>
              </div>
              <div className="flex gap-2">
                <button className="btn subtle" onClick={() => setConfirmClear(true)}>
                  <Trash2 size={14} /> Clear chat
                </button>
                <button className="btn subtle" onClick={() => setModelModal(true)}>
                  Model mode ▾
                </button>
              </div>
            </div>

            {/* Chat Message Scroll Area */}
            <div className="p-5 max-h-[540px] overflow-y-auto">
              {chatHistory.length ? (
                chatHistory.map((m, i) => (
                  <div key={i} className={m.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}>
                    <div className="bubble">
                      <div className="whitespace-pre-wrap">{m.text}</div>

                      {/* Display Grounded Source Citations if present */}
                      {m.sources && m.sources.length > 0 && (
                        <div className="mt-2.5 pt-2 border-t border-black/10 dark:border-white/10 text-xs">
                          <div className="font-semibold flex items-center gap-1 text-[var(--color-green-accent)] mb-1">
                            <Database size={12} /> Sources & Retrieved Material:
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {m.sources.map((s, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 rounded bg-black/5 dark:bg-white/10 text-[0.7rem] text-[var(--color-text-muted)] inline-flex items-center gap-1"
                                title={s.content_snippet || s.citation}
                              >
                                📄 {s.document_title || s.title || s.filename || 'Academic Chunk'}{' '}
                                {s.page_number ? `(Page ${s.page_number})` : ''}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="chat-time flex items-center justify-between mt-2 pt-1 border-t border-black/5 dark:border-white/10">
                        <span>{m.time}</span>
                        {m.role === 'assistant' && (
                          <button
                            onClick={() => copy(m.text, i)}
                            aria-label="Copy response"
                            className="text-inherit opacity-70 hover:opacity-100"
                          >
                            {copied === i ? <Check size={12} /> : <Copy size={12} />}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty-state">
                  <Sparkles size={28} />
                  <h3>Start a coursework conversation</h3>
                  <p>Ask a question about your uploaded documents or select a quick study tool below.</p>
                </div>
              )}
              {typing && (
                <div className="chat-bubble-ai">
                  <div className="bubble">Retrieving course chunks & formulating grounded explanation…</div>
                </div>
              )}
              <div ref={end} />
            </div>
          </div>

          {/* Active Document Selector Bar */}
          <div className="flex items-center gap-2 px-3 py-2 mb-2 text-xs rounded-xl bg-[var(--color-surface)] border border-[var(--color-border-light)] text-[var(--color-text-muted)]">
            <Database size={14} className="text-[var(--color-green-accent)] flex-shrink-0" />
            <span className="font-medium text-[var(--color-text-body)]">Active Document:</span>
            <select
              className="flex-1 bg-transparent border-0 outline-none text-xs text-[var(--color-text-dark)] font-medium cursor-pointer"
              value={materialId || ''}
              onChange={e => {
                const val = e.target.value;
                setMaterialId(val || null);
              }}
            >
              <option value="">All Accessible Course Materials</option>
              {documents.map(d => (
                <option key={d.id} value={d.id}>
                  📄 {d.name} ({d.id.slice(0, 8)}...)
                </option>
              ))}
            </select>
            {materialId && (
              <button
                type="button"
                onClick={() => {
                  setMaterialId(null);
                  setSubject(null);
                }}
                className="text-xs font-bold hover:text-red-500 cursor-pointer ml-2"
                title="Clear selected document"
              >
                Clear
              </button>
            )}
          </div>

          {/* Chat Input Bar */}
          <div className="flex gap-2 mb-3">
            <div className="flex-1 flex items-center gap-2 px-4 py-2.5 bg-[var(--color-card-bg)] border border-[var(--color-card-border)] rounded-xl">
              <input
                className="flex-1 bg-transparent outline-none text-sm text-[var(--color-text-dark)]"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && send()}
                placeholder="Ask about Paging, Deadlocks, TCP/UDP, Binary Search, or your uploaded documents…"
              />
              <button
                onClick={voice}
                aria-label="Voice input"
                className="text-[var(--color-text-muted)] hover:text-[var(--color-text-dark)]"
              >
                <Mic size={16} />
              </button>
            </div>
            <button
              onClick={() => send()}
              disabled={typing || !input.trim()}
              className="w-10 h-10 rounded-xl bg-[var(--color-green-accent)] text-white flex items-center justify-center disabled:opacity-50 cursor-pointer flex-shrink-0"
              aria-label="Send message"
            >
              <Send size={16} />
            </button>
          </div>

          {/* Quick Tool Filter Chips */}
          <div className="flex flex-wrap gap-2">
            {QUICK.map(([label, prompt]) => (
              <button key={label} className="filter-chip" onClick={() => selectTool(label, prompt)}>
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Right Sidebar: Tools & Prompts */}
        <div>
          <SectionHeader icon="⚡" title="Quick Study Tools" action="See all" onAction={() => setRecentModal(true)} />
          <div className="grid grid-cols-2 gap-3 mb-6">
            {QUICK.slice(0, 4).map(([label, prompt]) => (
              <button key={label} className="card text-left p-3 hover:border-[var(--color-green-accent)]" onClick={() => selectTool(label, prompt)}>
                <div className="text-lg mb-1.5">{label.split(' ')[0]}</div>
                <b className="text-xs block text-[var(--color-text-dark)]">{label.slice(2)}</b>
                <p className="text-[.62rem] text-[var(--color-text-muted)] mt-1 line-clamp-2">{prompt}</p>
              </button>
            ))}
          </div>

          <SectionHeader icon="💬" title="High-Yield Prompts" action="View all" onAction={() => setRecentModal(true)} />
          <div className="card mb-6 p-2 divide-y divide-[var(--color-border-light)]">
            {PROMPTS.map(p => (
              <button
                key={p}
                className="w-full text-left py-2.5 px-2 text-xs text-[var(--color-text-dark)] flex items-center justify-between hover:bg-[var(--color-green-light)]/40 rounded-lg transition-colors"
                onClick={() => {
                  setInput(p);
                  setRecentModal(false);
                }}
              >
                <span className="truncate pr-2">{p}</span>
                <span className="text-[var(--color-text-muted)] flex-shrink-0">→</span>
              </button>
            ))}
          </div>

          <div className="card p-3 text-xs text-[var(--color-text-muted)]">
            <div className="flex items-center gap-1.5 font-bold text-[var(--color-text-dark)] mb-1">
              <Info size={14} /> Grounded RAG Verification
            </div>
            Responses automatically retrieve chunks from your uploaded documents and attach exact filename and page citations.
          </div>
        </div>
      </div>

      {/* Tool Execution Modal */}
      <Modal open={!!tool} onClose={() => setTool(null)} title={tool || ''} subtitle="Customize prompt before asking AI">
        <textarea
          className="textarea"
          rows={5}
          value={input}
          onChange={e => setInput(e.target.value)}
        />
        <div className="modal-actions">
          <button className="btn secondary" onClick={() => setTool(null)}>
            Cancel
          </button>
          <button
            className="btn primary"
            onClick={() => {
              setTool(null);
              send();
            }}
          >
            <Sparkles size={15} /> Run prompt
          </button>
        </div>
      </Modal>

      {/* Model Selection Modal */}
      <Modal
        open={modelModal}
        onClose={() => setModelModal(false)}
        title="Choose AI Model Mode"
        subtitle="Select execution strategy for AcadAssist RAG responses"
      >
        <button
          className="card w-full text-left mb-2 p-3 hover:border-[var(--color-green-accent)]"
          onClick={() => {
            setModelName('Fast Study Mode (Azure OpenAI / Local Hybrid)');
            setModelModal(false);
            pushToast('Fast Study Mode selected');
          }}
        >
          <div className="flex justify-between items-center">
            <b>Fast Study Mode</b>
            <span className="soft-badge text-[.6rem]">Recommended</span>
          </div>
          <p className="muted text-xs mt-1">
            Concise explanations, rapid definition lookups, and fast quiz hints.
          </p>
        </button>

        <button
          className="card w-full text-left mb-2 p-3 hover:border-[var(--color-green-accent)]"
          onClick={() => {
            setModelName('Deep Reasoning Mode (Foundry Agent)');
            setModelModal(false);
            pushToast('Deep Reasoning Mode selected');
          }}
        >
          <div className="flex justify-between items-center">
            <b>Deep Reasoning Mode</b>
            <span className="soft-badge text-[.6rem]">11 Tools Active</span>
          </div>
          <p className="muted text-xs mt-1">
            Multi-step tool orchestration across Knowledge Search, Summarization, Quizzes, and Study Planner.
          </p>
        </button>

        <button
          className="card w-full text-left p-3 hover:border-[var(--color-green-accent)]"
          onClick={() => {
            setModelName('Deterministic Local RAG (Offline Safe)');
            setModelModal(false);
            pushToast('Deterministic Local Mode selected');
          }}
        >
          <div className="flex justify-between items-center">
            <b>Deterministic Local Assistant</b>
            <span className="soft-badge text-[.6rem]">Active Fallback</span>
          </div>
          <p className="muted text-xs mt-1">
            Built-in deterministic coursework question answering grounded in your local hybrid index.
          </p>
        </button>
      </Modal>

      {/* All Tools Modal */}
      <Modal open={recentModal} onClose={() => setRecentModal(false)} title="Study Tools & High-Yield Prompts">
        <div className="space-y-2">
          {QUICK.map(([label, prompt]) => (
            <button
              key={label}
              className="card w-full text-left p-3 flex justify-between items-center hover:border-[var(--color-green-accent)]"
              onClick={() => {
                setRecentModal(false);
                selectTool(label, prompt);
              }}
            >
              <div>
                <b className="text-xs block">{label}</b>
                <small className="text-[var(--color-text-muted)] text-[.65rem]">{prompt}</small>
              </div>
              <span className="text-[var(--color-text-muted)]">→</span>
            </button>
          ))}
        </div>
      </Modal>

      {/* Confirm Clear Chat Modal */}
      <Modal
        open={confirmClear}
        onClose={() => setConfirmClear(false)}
        title="Clear conversation history"
        subtitle="Removes saved chat messages from your account."
      >
        <p className="text-sm">Delete current conversation messages? Course documents, notes, and assessments will stay intact.</p>
        <div className="modal-actions">
          <button className="btn secondary" onClick={() => setConfirmClear(false)}>
            Cancel
          </button>
          <button
            className="btn danger"
            onClick={() => {
              clearChatHistory();
              setConfirmClear(false);
              pushToast('Chat history cleared', 'info');
            }}
          >
            Clear history
          </button>
        </div>
      </Modal>
    </div>
  );
}
