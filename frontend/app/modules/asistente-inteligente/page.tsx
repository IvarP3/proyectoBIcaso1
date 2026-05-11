'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import './page.css';

// ---------------------------------------------------------------------------
// Tipos — espejo del schema del backend (asistente_schema.py)
// ---------------------------------------------------------------------------

type MessageRole = 'user' | 'assistant' | 'system';

interface ChatMessage {
  role: MessageRole;
  content: string;
  timestamp: string;
  sources?: CitedSource[];
}

interface CitedSource {
  type: string;
  title: string;
  excerpt?: string;
  confidence?: number;
}

interface ChatResponse {
  answer: string;
  sources: CitedSource[];
  session_id: string | null;
  tokens_used: number | null;
  model_name: string | null;
  metadata: Record<string, unknown>;
}

interface SessionSummary {
  session_id: string;
  turns: number;
  preview?: string;
}

interface SessionDetailResponse {
  session_id: string;
  messages: ChatMessage[];
  total_turns: number;
  last_updated: string;
}

interface HealthResponse {
  status: string;
  llm_available: boolean;
  documents_indexed: number;
  message: string;
  version: string;
}

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------

const API_BASE_CANDIDATES = [
  process.env.NEXT_PUBLIC_API_BASE_URL
    ? `${process.env.NEXT_PUBLIC_API_BASE_URL.replace(/\/$/, '')}/asistente-inteligente`
    : null,
  'http://127.0.0.1:8000/api/v1/asistente-inteligente',
  'http://localhost:8000/api/v1/asistente-inteligente',
  '/api/v1/asistente-inteligente',
].filter(Boolean) as string[];

function pickApiBase(): string {
  return API_BASE_CANDIDATES[0] ?? '/api/v1/asistente-inteligente';
}

const MAX_CHARS = 4000;

const QUICK_SUGGESTIONS = [
  '¿Cuáles son los camiones con mayor riesgo en el ciclo actual?',
  '¿Qué contratos presentan mayor variación de margen?',
  'Resume los siniestros registrados este mes.',
  '¿Qué prescripciones están activas para las rutas del sur?',
];

const CAPABILITIES = [
  { icon: '📄', text: 'Consulta documentos y manuales operativos' },
  { icon: '📊', text: 'Analiza reportes de mermas y siniestros' },
  { icon: '🔍', text: 'Busca en criterios internos de TransFreezer' },
  { icon: '🚛', text: 'Relaciona datos con la Torre de Control SIO' },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function nowIso(): string {
  return new Date().toISOString().replace('T', ' ').slice(0, 19);
}

function formatTimestamp(ts: string): string {
  return ts.length >= 16 ? ts.slice(11, 16) : ts;
}

function shortSessionLabel(id: string, index: number): string {
  return `Sesión ${index + 1}`;
}

function collectVisibleScreenContext(route: string): Record<string, unknown> {
  if (typeof document === 'undefined') return {};

  const textNodes = Array.from(document.querySelectorAll('h1, h2, h3, p, li, th, td, .kpi-value, .metric-value'))
    .map((node) => node.textContent?.trim() ?? '')
    .filter(Boolean)
    .slice(0, 120);

  const visibleSummary = textNodes.join(' | ').slice(0, 2200);

  return {
    module: 'asistente-inteligente',
    route,
    page_title: document.title,
    visible_summary: visibleSummary,
  };
}

/**
 * Convierte texto Markdown del LLM a HTML seguro.
 * Maneja: tablas, headers (#), bold, italic, listas y saltos de línea.
 */
function renderMarkdown(raw: string): string {
  // 1. Escapar HTML primero
  let text = raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // 2. Tablas Markdown (bloques de líneas que empiezan con |)
  text = text.replace(
    /^(\|.+\|[ \t]*\n)(\|[-| :]+\|[ \t]*\n)((?:\|.+\|[ \t]*\n?)*)/gm,
    (_, headerLine: string, _sep: string, bodyLines: string) => {
      const parseRow = (line: string) =>
        line
          .replace(/^\|/, '')
          .replace(/\|$/, '')
          .split('|')
          .map((c) => c.trim());

      const headers = parseRow(headerLine);
      const rows = bodyLines
        .split('\n')
        .filter((l) => l.trim().startsWith('|'))
        .map(parseRow);

      const ths = headers
        .map((h) => `&lt;th&gt;${h}&lt;/th&gt;`)
        .join('');
      const trs = rows
        .map(
          (cells) =>
            `&lt;tr&gt;${cells.map((c) => `&lt;td&gt;${c}&lt;/td&gt;`).join('')}&lt;/tr&gt;`
        )
        .join('');

      return `&lt;div class="ai-md-table-wrap"&gt;&lt;table class="ai-md-table"&gt;&lt;thead&gt;&lt;tr&gt;${ths}&lt;/tr&gt;&lt;/thead&gt;&lt;tbody&gt;${trs}&lt;/tbody&gt;&lt;/table&gt;&lt;/div&gt;`;
    }
  );

  // Decodificar las etiquetas de tabla que escapamos arriba
  text = text
    .replace(/&lt;(\/?(?:div|table|thead|tbody|tr|th|td)[^&]*)&gt;/g, '<$1>')
    .replace(/class=&quot;/g, 'class="')
    .replace(/&quot;/g, '"');

  // 3. Headers (### ## #)
  text = text
    .replace(/^### (.+)$/gm, '<h4 class="ai-md-h">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 class="ai-md-h">$1</h3>')
    .replace(/^# (.+)$/gm, '<h2 class="ai-md-h">$1</h2>');

  // 4. Negrita e itálica
  text = text
    .replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>');

  // 5. Listas con guión
  text = text.replace(/^[-*] (.+)$/gm, '<li class="ai-md-li">$1</li>');
  text = text.replace(/(<li[^>]*>.*<\/li>\n?)+/g, (m) => `<ul class="ai-md-ul">${m}</ul>`);

  // 6. Listas numeradas
  text = text.replace(/^\d+\. (.+)$/gm, '<li class="ai-md-li">$1</li>');

  // 7. Líneas horizontales
  text = text.replace(/^---$/gm, '<hr class="ai-md-hr" />');

  // 8. Saltos de línea (fuera de bloques HTML ya procesados)
  text = text.replace(/\n(?!<(?:ul|li|h[2-4]|hr|div|table))/g, '<br />');

  return text;
}

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

export default function AsistenteInteligentePage() {
  const apiBase = useRef(pickApiBase()).current;
  const pathname = usePathname();

  // Estado de chat
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Estado del módulo
  const [health, setHealth] = useState<HealthResponse | null>(null);

  // Sesiones locales (historial de IDs de sesiones usadas en esta vista)
  const [sessionHistory, setSessionHistory] = useState<
    { id: string; label: string; preview: string }[]
  >([]);
  const [activeSessionIndex, setActiveSessionIndex] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ------------------------------------------------------------------
  // Health check
  // ------------------------------------------------------------------
  useEffect(() => {
    void fetchHealth();
    void fetchSessions();
  }, []);

  async function fetchHealth() {
    try {
      const res = await fetch(`${apiBase}/health`, { cache: 'no-store' });
      if (res.ok) {
        const data = (await res.json()) as HealthResponse;
        setHealth(data);
      }
    } catch {
      // Silencioso — el módulo muestra estado de preparación de todas formas
    }
  }

  async function fetchSessions(focusSessionId?: string) {
    try {
      const res = await fetch(`${apiBase}/sessions`, { cache: 'no-store' });
      if (!res.ok) return;
      const data = (await res.json()) as { sessions: SessionSummary[]; total: number };
      const mapped = data.sessions.map((session, index) => ({
        id: session.session_id,
        label: shortSessionLabel(session.session_id, index),
        preview: session.preview ?? `Turnos: ${session.turns}`,
      }));
      setSessionHistory(mapped);
      if (focusSessionId) {
        const activeIndex = mapped.findIndex((session) => session.id === focusSessionId);
        if (activeIndex >= 0) {
          setActiveSessionIndex(activeIndex);
        }
      }
    } catch {
      // Se mantiene la UI local si el backend no responde
    }
  }

  // ------------------------------------------------------------------
  // Auto-scroll al último mensaje
  // ------------------------------------------------------------------
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // ------------------------------------------------------------------
  // Auto-resize del textarea
  // ------------------------------------------------------------------
  const autoResizeTextarea = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }, []);

  useEffect(() => {
    autoResizeTextarea();
  }, [inputValue, autoResizeTextarea]);

  // ------------------------------------------------------------------
  // Enviar mensaje
  // ------------------------------------------------------------------
  async function sendMessage(text?: string) {
    const messageText = (text ?? inputValue).trim();
    if (!messageText || isLoading) return;

    setInputValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    const userTurn: ChatMessage = {
      role: 'user',
      content: messageText,
      timestamp: nowIso(),
    };

    const nextHistory = [...messages, userTurn];

    setMessages((prev) => [...prev, userTurn]);
    setIsLoading(true);

    try {
      const res = await fetch(`${apiBase}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageText,
          history: nextHistory,
          session_id: sessionId,
          context_hint: 'asistente-inteligente',
          screen_context: collectVisibleScreenContext(pathname),
        }),
        cache: 'no-store',
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = (await res.json()) as ChatResponse;

      const assistantTurn: ChatMessage = {
        role: 'assistant',
        content: data.answer,
        timestamp: nowIso(),
        sources: data.sources,
      };

      setMessages((prev) => [...prev, assistantTurn]);

      // Actualizar session_id
      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id);
        // Registrar en historial de sesiones
        await fetchSessions(data.session_id);
      }
    } catch (err) {
      const errorTurn: ChatMessage = {
        role: 'assistant',
        content:
          '⚠️ No se pudo contactar con el backend del asistente. Verifica que el servidor esté en ejecución.',
        timestamp: nowIso(),
      };
      setMessages((prev) => [...prev, errorTurn]);
    } finally {
      setIsLoading(false);
    }
  }

  // ------------------------------------------------------------------
  // Nueva sesión
  // ------------------------------------------------------------------
  function handleNewSession() {
    setMessages([]);
    setSessionId(null);
    setActiveSessionIndex(null);
  }

  // ------------------------------------------------------------------
  // Seleccionar sesión previa (solo visual por ahora)
  // ------------------------------------------------------------------
  async function handleSelectSession(index: number) {
    const session = sessionHistory[index];
    if (!session) return;

    setActiveSessionIndex(index);

    try {
      const res = await fetch(`${apiBase}/sessions/${session.id}`, { cache: 'no-store' });
      if (!res.ok) return;
      const data = (await res.json()) as SessionDetailResponse;
      setMessages(data.messages);
      setSessionId(data.session_id);
    } catch {
      // Si falla la restauración, se mantiene el selector visual.
    }
  }

  // ------------------------------------------------------------------
  // Limpiar chat visible
  // ------------------------------------------------------------------
  function handleClearChat() {
    setMessages([]);
  }

  // ------------------------------------------------------------------
  // Teclas del textarea
  // ------------------------------------------------------------------
  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void sendMessage();
    }
  }

  const charsLeft = MAX_CHARS - inputValue.length;
  const charsWarn = charsLeft < 200;

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------
  return (
    <div className="ai-page">
      {/* ---- HEADER ---- */}
      <header className="ai-header">
        <div className="ai-header-brand">
          <div className="ai-header-icon" aria-hidden="true">🤖</div>
          <div className="ai-header-copy">
            <h1 className="ai-header-title">Asistente Inteligente</h1>
            <p className="ai-header-sub">PLN · TransFreezer Insight Suite</p>
          </div>
        </div>

        <div className="ai-header-actions">
          <span className="ai-status-pill">
            <span className="ai-status-pill__dot" />
            {health?.llm_available ? 'Operativo' : 'En preparación'}
          </span>
          {messages.length > 0 && (
            <button
              type="button"
              className="ai-clear-btn"
              onClick={handleClearChat}
              title="Limpiar conversación visible"
            >
              Limpiar chat
            </button>
          )}
        </div>
      </header>

      {/* ---- BODY ---- */}
      <div className="ai-body">
        {/* ---- SIDEBAR ---- */}
        <aside className="ai-sidebar">
          {/* Nueva sesión */}
          <div className="ai-sidebar-section">
            <p className="ai-sidebar-section-title">Sesiones</p>
            <button
              type="button"
              className="ai-new-session-btn"
              onClick={handleNewSession}
            >
              <span aria-hidden="true">＋</span>
              Nueva sesión
            </button>
          </div>

          {/* Historial de sesiones */}
          <div className="ai-sessions-list">
            {sessionHistory.length === 0 ? (
              <p style={{ fontSize: '0.78rem', color: '#3d4e63', padding: '0.5rem 0.25rem' }}>
                Aquí aparecerán tus conversaciones.
              </p>
            ) : (
              sessionHistory.map((session, idx) => (
                <button
                  key={session.id}
                  type="button"
                  className={`ai-session-item ${activeSessionIndex === idx ? 'ai-session-item--active' : ''}`}
                  onClick={() => handleSelectSession(idx)}
                >
                  <span className="ai-session-item__icon">💬</span>
                  <span className="ai-session-item__label">{session.label}</span>
                  <span className="ai-session-item__meta">{session.preview.slice(0, 16)}…</span>
                </button>
              ))
            )}
          </div>

          {/* Capacidades del módulo */}
          <div className="ai-capabilities">
            <p className="ai-sidebar-section-title" style={{ padding: '0 0.25rem' }}>
              Capacidades
            </p>
            {CAPABILITIES.map((cap) => (
              <div key={cap.text} className="ai-capability-item">
                <span className="ai-capability-item__icon">{cap.icon}</span>
                <span className="ai-capability-item__text">{cap.text}</span>
              </div>
            ))}
          </div>
        </aside>

        {/* ---- ÁREA DE CHAT ---- */}
        <div className="ai-chat-area">
          {/* Mensajes o pantalla de bienvenida */}
          {messages.length === 0 && !isLoading ? (
            <div className="ai-welcome">
              <div className="ai-welcome__icon" aria-hidden="true">🤖</div>
              <h2 className="ai-welcome__title">Asistente Inteligente</h2>
              <p className="ai-welcome__subtitle">
                Consulta documentos, reportes operativos y criterios internos de TransFreezer
                de forma conversacional. El módulo PLN estará completamente activo en la próxima
                iteración.
              </p>
              <span className="ai-welcome__badge">
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#f6d36b', display: 'inline-block' }} />
                {health?.message ?? 'En preparación'}
              </span>
              <span className="ai-welcome__badge" style={{ marginTop: '0.5rem' }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#7fb6dc', display: 'inline-block' }} />
                {health?.documents_indexed ?? 0} alertas indexadas
              </span>

              {/* Sugerencias rápidas */}
              <div className="ai-suggestions">
                {QUICK_SUGGESTIONS.map((sug) => (
                  <button
                    key={sug}
                    type="button"
                    className="ai-suggestion-btn"
                    onClick={() => void sendMessage(sug)}
                  >
                    {sug}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="ai-messages" role="log" aria-live="polite" aria-label="Conversación">
              {messages.map((msg, idx) => (
                <div
                  key={`${msg.role}-${idx}`}
                  className={`ai-message ai-message--${msg.role}`}
                >
                  <div className="ai-message__avatar" aria-hidden="true">
                    {msg.role === 'user' ? 'US' : '🤖'}
                  </div>
                  <div>
                    <div
                      className="ai-message__bubble"
                      dangerouslySetInnerHTML={{
                        __html: renderMarkdown(msg.content),
                      }}
                    />
                    <p className="ai-message__time">{formatTimestamp(msg.timestamp)}</p>
                    {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 ? (
                      <div className="ai-message__sources">
                        <p className="ai-message__sources-title">Fuentes recuperadas</p>
                        <div className="ai-message__source-list">
                          {msg.sources.map((source, sIdx) => (
                            <div key={`${source.title}-${source.type}-${sIdx}`} className="ai-message__source-item">
                              <strong>{source.title}</strong>
                              <span>{source.excerpt ?? '—'}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>
              ))}

              {/* Indicador de escritura */}
              {isLoading && (
                <div className="ai-message ai-message--assistant">
                  <div className="ai-message__avatar" aria-hidden="true">🤖</div>
                  <div className="ai-message__bubble">
                    <div className="ai-typing-indicator" aria-label="El asistente está escribiendo">
                      <span className="ai-typing-indicator__dot" />
                      <span className="ai-typing-indicator__dot" />
                      <span className="ai-typing-indicator__dot" />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}

          {/* ---- INPUT AREA ---- */}
          <div className="ai-input-area">
            <div className="ai-input-wrapper">
              <textarea
                ref={textareaRef}
                id="ai-chat-input"
                className="ai-input"
                placeholder="Escribe tu consulta… (Enter para enviar, Shift+Enter para nueva línea)"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value.slice(0, MAX_CHARS))}
                onKeyDown={handleKeyDown}
                rows={1}
                aria-label="Mensaje para el asistente"
                disabled={isLoading}
              />
              <button
                id="ai-send-btn"
                type="button"
                className="ai-send-btn"
                onClick={() => void sendMessage()}
                disabled={isLoading || !inputValue.trim()}
                aria-label="Enviar mensaje"
              >
                {/* Icono de flecha de envío */}
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path
                    d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </div>
            <div className="ai-input-meta">
              <span className="ai-input-hint">
                Enter para enviar · Shift+Enter para nueva línea
              </span>
              <span className={`ai-input-chars ${charsWarn ? 'ai-input-chars--warn' : ''}`}>
                {inputValue.length > 0 ? `${charsLeft} caracteres restantes` : ''}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
