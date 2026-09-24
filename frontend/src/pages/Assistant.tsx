import { useEffect, useRef, useState } from 'react';
import { Send, Mic, Sparkles, Trash2, Copy, Check, Bot, Database, Info } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import HeroHeader from '../components/ui/HeroHeader';
import SectionHeader from '../components/ui/SectionHeader';
import Modal from '../components/ui/Modal';
import { useApp } from '../context/AppContext';
import {
  chatWithAssistant,
  fetchDocuments,
  fetchHealthStatus,
  formatApiError,
  type DocumentUploadResponse
} from '../services/api';

const QUICK = [
  ['💡 Explain Concept', 'Explain Deadlock Coffman conditions in simple language with an example'],
  ['📝 Summarize Material', 'Summarize key points and exam criteria for TCP vs UDP flow control'],
  ['📄 High-Yield Notes', 'Create exam-ready revision notes for B+ tree indexing'],
  ['⚖️ Compare Topics', 'Compare Deadlock Prevention vs Deadlock Avoidance'],
  ['🎯 Create Practice', 'Generate 5 conceptual questions on CPU scheduling algorithms'],
];

const PROMPTS = [
  'Explain the 4 Coffman conditions required for deadlock',
  'What is the difference between TCP and UDP sliding window?',
  'Explain BCNF decomposition and why it avoids update anomalies',
  'How does Round Robin scheduling choose the time quantum?',
  'Walk through Banker’s algorithm safety state evaluation',
];

export default function Assistant() {
  const { chatHistory, addChatMessage, clearChatHistory, pushToast } = useApp();
  const [params] = useSearchParams();

  const [input, setInput] = useState('');
  const [materialId, setMaterialId] = useState<string | null>(null);
  const [subject, setSubject] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentUploadResponse[]>([]);
  const [typing, setTyping] = useState(false);
  const [loadingStage, setLoadingStage] = useState('');
  const [tool, setTool] = useState<string | null>(null);
  const [modelModal, setModelModal] = useState(false);
  const [recentModal, setRecentModal] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  const [modelName, setModelName] = useState('Checking AI status...');
  const [engineState, setEngineState] = useState<'connected' | 'fallback' | 'unavailable'>('fallback');
  const [engineDetail, setEngineDetail] = useState('Operating via Local AI Orchestrator');
  const [copied, setCopied] = useState<number | null>(null);
  const end = useRef<HTMLDivElement>(null);

  // Preload prompt and material context from URL if navigated from Knowledge / Assessment
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

  // Load available documents so student can select active document
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

  // Dynamic AI status check via backend /health
  useEffect(() => {
    fetchHealthStatus()
      .then(health => {
        if (!health) {
          setEngineState('unavailable');
          setEngineDetail('AI service is currently unreachable');
          setModelName('AI Service Offline');
          return;
        }
        if (health.foundry?.configured || health.foundry?.mode === 'cloud_foundry') {
          setEngineState('connected');
          setEngineDetail('Connected to Azure OpenAI & Microsoft Foundry (gpt-4.1-mini)');
          setModelName('Microsoft Foundry (gpt-4.1-mini)');
        } else if (health.status === 'healthy') {
          setEngineState('fallback');
          setEngineDetail('Operating via Local AI Orchestrator & Hybrid Search');
          setModelName('Local AI / Fallback Mode');
        } else {
          setEngineState('unavailable');
          setEngineDetail('AI service is currently unavailable');
          setModelName('AI Service Unavailable');
        }
      })
      .catch(() => {
        setEngineState('unavailable');
        setEngineDetail('AI service is currently unreachable');
        setModelName('AI Service Offline');
      });
  }, []);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, typing, loadingStage]);

  const send = async (text = input) => {
    const value = text.trim();
    if (!value || typing) return;
    setInput('');
    addChatMessage('user', value);
    setTyping(true);
    setLoadingStage('🔎 Searching study material...');

    const stageTimer1 = window.setTimeout(() => {
      setLoadingStage('🧠 Generating grounded response...');
    }, 1100);

    const stageTimer2 = window.setTimeout(() => {
      setLoadingStage('📚 Grounding response & preparing sources...');
    }, 2400);

    try {
      const context = materialId ? { materialId, ...(subject ? { subject } : {}) } : undefined;
      const r = await chatWithAssistant(value, context);
      if (r.executionMode === 'cloud_foundry') {
        setEngineState('connected');
        setModelName('Microsoft Foundry (gpt-4.1-mini)');
      }
      addChatMessage('assistant', r.text, r.sources, r.actions);
    } catch (e) {
      console.error('AI chat error:', e);
      addChatMessage(
        'assistant',
        formatApiError(e, "AcadAssist couldn't generate a response right now. Please try again.")
      );
    } finally {
      window.clearTimeout(stageTimer1);
      window.clearTimeout(stageTimer2);
      setTyping(false);
      setLoadingStage('');
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
        subtitle="Clarify doubts, explain course concepts, generate summaries, and prepare for upcoming exams."
      />

      {/* Accurate AI Status Presentation (Task 2) */}
      <div
        className={`card p-3 flex items-center justify-between text-xs transition-colors ${
          engineState === 'connected'
            ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-200 border-emerald-200 dark:border-emerald-800/40'
            : engineState === 'fallback'
            ? 'bg-amber-50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200 border-amber-200 dark:border-amber-800/40'
            : 'bg-red-50 dark:bg-red-950/30 text-red-800 dark:text-red-200 border-red-200 dark:border-red-800/40'
        }`}
      >
        <div className="flex items-center gap-2">
          <Bot size={16} />
          <span>
            <b>
              {engineState === 'connected'
                ? 'AI Engine Connected:'
                : engineState === 'fallback'
                ? 'Local AI / Fallback Mode:'
                : 'AI Service Unavailable:'}
            </b>{' '}
            {engineDetail}
          </span>
        </div>
        <span
          className={`font-bold text-[.68rem] px-2.5 py-1 rounded-md flex items-center gap-1.5 ${
            engineState === 'connected'
              ? 'bg-emerald-100 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-200'
              : engineState === 'fallback'
              ? 'bg-amber-100 dark:bg-amber-900/60 text-amber-800 dark:text-amber-200'
              : 'bg-red-100 dark:bg-red-900/60 text-red-800 dark:text-red-200'
          }`}
        >
          {engineState === 'connected'
            ? '🟢 AI Engine Connected'
            : engineState === 'fallback'
            ? '🟡 Local AI/Fallback Mode'
            : '🔴 AI Service Unavailable'}
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
                <span
                  className={`ml-2 text-[.68rem] font-semibold ${
                    engineState === 'connected'
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : engineState === 'fallback'
                      ? 'text-amber-600 dark:text-amber-400'
                      : 'text-red-500'
                  }`}
                >
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

                      {/* Display Grounded Source Citations (Task 7) */}
                      {m.sources && m.sources.length > 0 && (
                        <div className="mt-3 pt-2.5 border-t border-black/10 dark:border-white/10 text-xs">
                          <div className="font-bold flex items-center justify-between text-[var(--color-green-accent)] mb-2">
                            <div className="flex items-center gap-1.5">
                              <Database size={13} />
                              <span>Sources & Retrieved Material</span>
                            </div>
                            <span className="text-[0.62rem] font-medium text-[var(--color-text-muted)]">
                              Grounded in course notes
                            </span>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {m.sources.map((s, idx) => (
                              <div
                                key={idx}
                                className="p-2 rounded-lg bg-black/5 dark:bg-white/5 border border-black/5 dark:border-white/10 flex flex-col justify-between"
                              >
                                <div className="flex items-start gap-1.5 min-w-0">
                                  <span className="text-sm leading-none flex-shrink-0 mt-0.5">📄</span>
                                  <div className="min-w-0 flex-1">
                                    <b className="text-xs text-[var(--color-text-dark)] truncate block" title={s.document_title || s.filename}>
                                      {s.document_title || s.filename || 'Academic Document'}
                                    </b>
                                    <div className="flex items-center gap-2 mt-0.5 text-[0.68rem] text-[var(--color-text-muted)]">
                                      {s.page_number ? <span>Page {s.page_number}</span> : s.slide_number ? <span>Slide {s.slide_number}</span> : <span>Verified Chunk</span>}
                                      {s.score !== undefined && (
                                        <span className="px-1.5 py-0.2 rounded bg-black/5 dark:bg-white/10 text-[0.62rem]">
                                          {Math.round(s.score * 100)}% match
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                {s.content_snippet && (
                                  <p className="text-[0.65rem] text-[var(--color-text-muted)] mt-1.5 line-clamp-2 italic bg-black/5 dark:bg-black/20 p-1.5 rounded">
                                    "{s.content_snippet}"
                                  </p>
                                )}
                              </div>
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
                <div className="empty-state py-8">
                  <div className="text-3xl mb-2">💬</div>
                  <h3 className="text-base font-bold text-[var(--color-text-dark)]">Ask AcadAssist about your study material</h3>
                  <p className="text-xs text-[var(--color-text-muted)] max-w-md mx-auto mt-1 mb-4">
                    Clarify doubts, explain course concepts, generate summaries, and prepare for upcoming exams.
                  </p>
                  <div className="flex flex-wrap justify-center gap-2 max-w-lg mx-auto">
                    {PROMPTS.slice(0, 3).map((pText, pIdx) => (
                      <button
                        key={pIdx}
                        className="btn secondary text-xs text-left"
                        onClick={() => {
                          setInput(pText);
                          send(pText);
                        }}
                      >
                        <Sparkles size={12} className="text-[var(--color-green-accent)] flex-shrink-0" />
                        <span className="truncate max-w-[280px]">{pText}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {typing && (
                <div className="chat-bubble-ai">
                  <div className="bubble flex items-center gap-2.5 py-3">
                    <Sparkles size={16} className="text-[var(--color-green-accent)] animate-spin flex-shrink-0" />
                    <span className="text-xs font-medium text-[var(--color-text-dark)]">
                      {loadingStage || 'Generating study response...'}
                    </span>
                  </div>
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
              <option value="">None (General Course Materials)</option>
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
                onKeyDown={e => {
                  if (e.key === 'Enter' && !typing && input.trim()) {
                    send();
                  }
                }}
                disabled={typing}
                placeholder={typing ? 'AcadAssist is formulating your grounded response...' : 'Ask about Deadlocks, TCP/UDP, Normalization, or problem derivations…'}
              />
              <button
                onClick={voice}
                aria-label="Voice input"
                disabled={typing}
                className="text-[var(--color-text-muted)] hover:text-[var(--color-text-dark)] disabled:opacity-40"
              >
                <Mic size={16} />
              </button>
            </div>
            <button
              onClick={() => send()}
              disabled={typing || !input.trim()}
              className="w-10 h-10 rounded-xl bg-[var(--color-green-accent)] text-white flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer flex-shrink-0 transition-opacity"
              aria-label="Send message"
            >
              {typing ? <Sparkles size={16} className="animate-spin" /> : <Send size={16} />}
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
              <Info size={14} /> Azure AI Integration Point
            </div>
            When Person 1 connects Azure OpenAI / Foundry in <code>src/services/api.ts</code>, responses will automatically stream from your deployed models.
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
        subtitle="Frontend representation of deployment configurations for Azure integration"
      >
        <button
          className="card w-full text-left mb-2 p-3 hover:border-[var(--color-green-accent)]"
          onClick={() => {
            setModelName('Fast Study Mode (Azure OpenAI Ready)');
            setModelModal(false);
            pushToast('Fast Study Mode selected');
          }}
        >
          <div className="flex justify-between items-center">
            <b>Fast Study Mode</b>
            <span className="soft-badge text-[.6rem]">Demo Mode</span>
          </div>
          <p className="muted text-xs mt-1">
            Concise explanations, rapid definition lookups, and fast quiz hints. Prepared for <code>gpt-4o-mini</code>.
          </p>
        </button>

        <button
          className="card w-full text-left mb-2 p-3 hover:border-[var(--color-green-accent)]"
          onClick={() => {
            setModelName('Deep Reasoning Mode (Foundry Ready)');
            setModelModal(false);
            pushToast('Deep Reasoning Mode selected');
          }}
        >
          <div className="flex justify-between items-center">
            <b>Deep Reasoning Mode</b>
            <span className="soft-badge text-[.6rem]">Demo Mode</span>
          </div>
          <p className="muted text-xs mt-1">
            Formal proofs, step-by-step mathematical derivations, and code simulations. Prepared for Azure AI Foundry reasoning endpoints.
          </p>
        </button>

        <button
          className="card w-full text-left p-3 hover:border-[var(--color-green-accent)]"
          onClick={() => {
            setModelName('Deterministic Local Mode (Offline)');
            setModelModal(false);
            pushToast('Deterministic Local Mode selected');
          }}
        >
          <div className="flex justify-between items-center">
            <b>Deterministic Local Assistant</b>
            <span className="soft-badge text-[.6rem]">Active Fallback</span>
          </div>
          <p className="muted text-xs mt-1">
            Built-in deterministic coursework question answering. Operates offline without external network dependency.
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
        subtitle="This only removes local chat messages in this browser."
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
