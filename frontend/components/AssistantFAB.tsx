'use client';

import { usePathname } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';
import './AssistantFAB.css';

// ---------------------------------------------------------------------------
// Rutas donde el FAB aparece
// ---------------------------------------------------------------------------
const VISIBLE_PATHS = [
  '/',
  '/modules/torre-control-sio',
  '/modules/forecast',
  '/modules/econometria',
];

function shouldShowFAB(pathname: string): boolean {
  return VISIBLE_PATHS.some((p) =>
    p === '/' ? pathname === '/' : pathname === p || pathname.startsWith(`${p}/`)
  );
}

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------
type MessageRole = 'user' | 'assistant';

interface Message {
  role: MessageRole;
  content: string;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------
const API_BASE = (() => {
  const env = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (env) return `${env.replace(/\/$/, '')}/asistente-inteligente`;
  return 'http://127.0.0.1:8000/api/v1/asistente-inteligente';
})();

const MAX_CHARS = 1000;
const QUICK_PROMPTS = [
  '¿Qué camiones tienen mayor riesgo?',
  '¿Cuál es el margen proyectado?',
  'Resume las alertas activas.',
];

function nowTime(): string {
  return new Date().toLocaleTimeString('es-BO', { hour: '2-digit', minute: '2-digit' });
}

function inferModuleFromPath(pathname: string): string {
  if (pathname.includes('/econometria')) return 'econometria';
  if (pathname.includes('/forecast')) return 'forecast-operativo';
  if (pathname.includes('/torre-control-sio')) return 'torre-control-sio';
  if (pathname === '/') return 'home';
  return 'desconocido';
}

function collectVisibleScreenContext(pathname: string): Record<string, unknown> {
  if (typeof document === 'undefined') return {};

  const summaryParts = Array.from(
    document.querySelectorAll('h1, h2, h3, p, li, th, td, .kpi-value, .metric-value, .stat-value')
  )
    .map((node) => node.textContent?.trim() ?? '')
    .filter(Boolean)
    .slice(0, 140);

  return {
    module: inferModuleFromPath(pathname),
    route: pathname,
    page_title: document.title,
    visible_summary: summaryParts.join(' | ').slice(0, 2600),
  };
}

/**
 * Convierte texto Markdown del LLM a HTML seguro.
 * Maneja: tablas, headers (#), bold, italic, listas y saltos de linea.
 */
function renderMarkdown(raw: string): string {
  // 1. Escapar HTML primero
  let text = raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // 2. Tablas Markdown (bloques de lineas que empiezan con |)
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

  // 4. Negrita e italica
  text = text
    .replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>');

  // 5. Listas con guion
  text = text.replace(/^[-*] (.+)$/gm, '<li class="ai-md-li">$1</li>');
  text = text.replace(/(<li[^>]*>.*<\/li>\n?)+/g, (m) => `<ul class="ai-md-ul">${m}</ul>`);

  // 6. Listas numeradas
  text = text.replace(/^\d+\. (.+)$/gm, '<li class="ai-md-li">$1</li>');

  // 7. Lineas horizontales
  text = text.replace(/^---$/gm, '<hr class="ai-md-hr" />');

  // 8. Saltos de linea (fuera de bloques HTML ya procesados)
  text = text.replace(/\n(?!<(?:ul|li|h[2-4]|hr|div|table))/g, '<br />');

  return text;
}

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------
export default function AssistantFAB() {
  const pathname = usePathname();

  // Visibilidad del FAB en la página
  const [fabVisible, setFabVisible] = useState(false);
  // Panel de chat abierto/cerrado
  const [chatOpen, setChatOpen] = useState(false);
  // Montado (evita hydration mismatch)
  const [mounted, setMounted] = useState(false);

  // Estado del chat
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // ---- Montaje ----
  useEffect(() => { setMounted(true); }, []);

  // ---- Visibilidad según ruta ----
  useEffect(() => {
    if (!mounted) return;
    const show = shouldShowFAB(pathname);
    if (show) {
      const t = setTimeout(() => setFabVisible(true), 120);
      return () => clearTimeout(t);
    } else {
      setFabVisible(false);
      setChatOpen(false); // Cierra el panel al cambiar de ruta
    }
  }, [pathname, mounted]);

  // ---- Auto-scroll ----
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // ---- Auto-resize textarea ----
  const autoResize = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 120)}px`;
  }, []);

  useEffect(() => { autoResize(); }, [inputValue, autoResize]);

  // ---- Cerrar con Escape ----
  useEffect(() => {
    if (!chatOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setChatOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [chatOpen]);

  // ---- Enviar mensaje ----
  async function sendMessage(text?: string) {
    const msg = (text ?? inputValue).trim();
    if (!msg || isLoading) return;

    setInputValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    const userTurn: Message = { role: 'user', content: msg, timestamp: nowTime() };
    setMessages((prev) => [...prev, userTurn]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: msg,
          history: messages,
          session_id: sessionId,
          context_hint: pathname,
          screen_context: collectVisibleScreenContext(pathname),
        }),
        cache: 'no-store',
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const asTurn: Message = {
        role: 'assistant',
        content: data.answer ?? '—',
        timestamp: nowTime(),
      };
      setMessages((prev) => [...prev, asTurn]);
      if (data.session_id) setSessionId(data.session_id);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '⚠️ No pude conectar con el asistente. Verifica que el servidor esté activo.',
          timestamp: nowTime(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void sendMessage();
    }
  }

  function toggleChat() {
    setChatOpen((prev) => !prev);
  }

  function clearChat() {
    setMessages([]);
    setSessionId(null);
  }

  if (!mounted) return null;

  const charsLeft = MAX_CHARS - inputValue.length;

  return (
    <div
      className={`fab-root ${fabVisible ? 'fab-root--visible' : ''}`}
      aria-hidden={!fabVisible}
    >
      {/* ================================================================
          PANEL DE CHAT FLOTANTE
      ================================================================ */}
      <div
        ref={panelRef}
        className={`fab-panel ${chatOpen ? 'fab-panel--open' : ''}`}
        role="dialog"
        aria-label="Mini chat del Asistente Inteligente"
        aria-modal="false"
      >
        {/* Header del panel */}
        <div className="fab-panel__header">
          <div className="fab-panel__header-brand">
            <span className="fab-panel__avatar" aria-hidden="true">🤖</span>
            <div>
              <p className="fab-panel__title">Asistente Inteligente</p>
              <p className="fab-panel__subtitle">PLN · TransFreezer</p>
            </div>
          </div>
          <div className="fab-panel__header-actions">
            {messages.length > 0 && (
              <button
                type="button"
                className="fab-panel__icon-btn"
                onClick={clearChat}
                title="Limpiar conversación"
                aria-label="Limpiar conversación"
              >
                {/* Icono de papelera */}
                <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                  <path d="M8 3h4M3 6h14M5 6l1 11h8l1-11" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            )}
            <button
              type="button"
              className="fab-panel__icon-btn"
              onClick={() => setChatOpen(false)}
              title="Cerrar"
              aria-label="Cerrar chat"
            >
              {/* Icono X */}
              <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
            </button>
          </div>
        </div>

        {/* Área de mensajes */}
        <div className="fab-panel__messages" role="log" aria-live="polite">
          {messages.length === 0 ? (
            <div className="fab-panel__welcome">
              <p className="fab-panel__welcome-text">
                ¡Hola! Soy tu asistente. ¿En qué puedo ayudarte?
              </p>
              <div className="fab-panel__quick-prompts">
                {QUICK_PROMPTS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="fab-panel__quick-btn"
                    onClick={() => void sendMessage(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                className={`fab-msg fab-msg--${msg.role}`}
              >
                {msg.role === 'assistant' && (
                  <span className="fab-msg__avatar" aria-hidden="true">🤖</span>
                )}
                <div className="fab-msg__body">
                  <div
                    className="fab-msg__bubble"
                    dangerouslySetInnerHTML={{
                      __html: renderMarkdown(msg.content),
                    }}
                  />
                  <span className="fab-msg__time">{msg.timestamp}</span>
                </div>
              </div>
            ))
          )}

          {/* Indicador de escritura */}
          {isLoading && (
            <div className="fab-msg fab-msg--assistant">
              <span className="fab-msg__avatar" aria-hidden="true">🤖</span>
              <div className="fab-msg__body">
                <div className="fab-msg__bubble fab-msg__bubble--typing">
                  <span className="fab-typing-dot" />
                  <span className="fab-typing-dot" />
                  <span className="fab-typing-dot" />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="fab-panel__input-area">
          <div className="fab-panel__input-wrapper">
            <textarea
              ref={textareaRef}
              className="fab-panel__textarea"
              placeholder="Escribe tu consulta…"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value.slice(0, MAX_CHARS))}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={isLoading}
              aria-label="Mensaje al asistente"
            />
            <button
              type="button"
              className="fab-panel__send-btn"
              onClick={() => void sendMessage()}
              disabled={isLoading || !inputValue.trim()}
              aria-label="Enviar"
            >
              <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path d="M18 2L9 11M18 2L12 18 9 11 2 8l16-6z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
          {inputValue.length > MAX_CHARS * 0.8 && (
            <p className="fab-panel__chars">{charsLeft} restantes</p>
          )}
        </div>
      </div>

      {/* ================================================================
          BOTÓN FAB PRINCIPAL
      ================================================================ */}
      <button
        id="assistant-fab-btn"
        type="button"
        className={`assistant-fab ${chatOpen ? 'assistant-fab--open' : ''}`}
        onClick={toggleChat}
        aria-label={chatOpen ? 'Cerrar asistente' : 'Abrir Asistente Inteligente'}
        aria-expanded={chatOpen}
      >
        {/* Anillo de pulso (solo cuando cerrado) */}
        {!chatOpen && <span className="assistant-fab__ring" aria-hidden="true" />}

        {/* Badge de mensajes no leídos (futuro) */}
        {!chatOpen && <span className="assistant-fab__badge" aria-hidden="true" />}

        {/* Icono: chat cuando cerrado, X cuando abierto */}
        <span className={`assistant-fab__icon-wrap ${chatOpen ? 'assistant-fab__icon-wrap--open' : ''}`}>
          {/* Ícono chat */}
          <svg className="assistant-fab__icon assistant-fab__icon--chat" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 3C7.03 3 3 6.58 3 11c0 2.17.9 4.14 2.37 5.6L4 21l4.6-1.5A9.18 9.18 0 0012 20c4.97 0 9-3.58 9-8s-4.03-9-9-9z" fill="currentColor" opacity="0.18" />
            <path d="M12 3C7.03 3 3 6.58 3 11c0 2.17.9 4.14 2.37 5.6L4 21l4.6-1.5A9.18 9.18 0 0012 20c4.97 0 9-3.58 9-8s-4.03-9-9-9z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
            <circle cx="8.5" cy="11" r="1" fill="currentColor" />
            <circle cx="12" cy="11" r="1" fill="currentColor" />
            <circle cx="15.5" cy="11" r="1" fill="currentColor" />
          </svg>
          {/* Ícono X */}
          <svg className="assistant-fab__icon assistant-fab__icon--close" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
          </svg>
        </span>
      </button>
    </div>
  );
}
