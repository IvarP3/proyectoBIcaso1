from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.modules.asistente_inteligente.repositories.asistente_repository import AsistenteSQLiteRepository
from app.modules.asistente_inteligente.schemas.asistente_schema import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    CitedSource,
    HealthResponse,
    MessageRole,
    SessionClearResponse,
    SessionDetailResponse,
    SessionListResponse,
    SourceType,
)

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    requests = None  # type: ignore

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    BeautifulSoup = None  # type: ignore

try:
    import spacy  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    spacy = None  # type: ignore

try:
    from transformers import pipeline  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pipeline = None  # type: ignore

try:
    import google.generativeai as genai  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    genai = None  # type: ignore


_MAX_HISTORY_TURNS = 20
_MODULE_VERSION = '2.0.0-poc'
_MAX_CONTEXT_ALERTS = 5
_ZERO_SHOT_MAX_CHARS = 800
_NER_MAX_CHARS = 1200

FUENTES: dict[str, str] = {
    'SENAMHI Alertas': 'https://www.senamhi.gob.bo/alertas2.php',
    'ABC Oficial': 'https://www.abc.gob.bo/',
    'Unitel Noticias': 'https://unitel.bo/',
    'El Deber': 'https://eldeber.com.bo/',
    'Erbol': 'https://www.erbol.com.bo/',
}

ETIQUETAS_RIESGO = [
    'Bloqueo de carretera',
    'Desastre Natural/Clima',
    'Accidente',
    'Tránsito Normal',
]

EMOJIS_CATEGORIA = {
    'Bloqueo de carretera': '🚧',
    'Desastre Natural/Clima': '🌧️',
    'Accidente': '🚨',
    'Tránsito Normal': '✅',
}

TOPONIMOS_BOLIVIA = [
    'Yapacaní', 'Yapacani', 'El Sillar', 'Caranavi', 'Coroico', 'Pazña', 'Pazna',
    'Filadelfia', 'Bella Flor', 'Puerto Rico', 'Cobija', 'Porvenir', 'Trinidad',
    'Puerto Suárez', 'Entre Ríos', 'Bermejo', 'Rurrenabaque', 'Challapata', 'Aiquile',
    'El Palmar', 'Los Túneles', 'La Paz', 'Santa Cruz', 'Cochabamba', 'Oruro',
    'Potosí', 'Tarija', 'Beni', 'Pando', 'Chuquisaca', 'Bolivia', 'Yungas',
    'Bioceánica', 'Bioceanica', 'Palmar', 'Puerto Suarez',
]

MODELOS_FALLBACK = [
    'gemini-2.0-flash',
    'models/gemini-3.1-flash-lite',
    'models/gemini-3-flash',
    'models/gemini-2.5-flash',
]

SYSTEM_PROMPT_GEMINI = """Eres el Asistente de Inteligencia Vial de TransFreezer Bolivia S.R.L.

Tu función principal es asistir a la Torre de Control con información precisa, clara, accionable y 
operativamente útil sobre el estado de las carreteras bolivianas. Debes actuar como un analista vial 
especializado en logística de cadena de frío, capaz de interpretar alertas, eventos, reportes, estados 
de ruta, bloqueos, accidentes, clima, demoras, riesgos operativos y datos estructurados provenientes del 
sistema interno.

CONTEXTO DE LA EMPRESA:
- Operamos una flota de camiones frigoríficos en todo el territorio boliviano.
- Transportamos productos de cadena de frío, incluyendo alimentos, medicamentos, insumos sensibles 
a temperatura y otros productos perecederos o de alto valor.
- Las rutas principales son: La Paz-Santa Cruz, especialmente el tramo de El Sillar; Cochabamba-Santa Cruz, 
especialmente Yapacaní; Oruro-Potosí; Tarija-Bermejo; La Paz-Rurrenabaque, incluyendo zonas de Yungas; 
Santa Cruz-Puerto Suárez, correspondiente a la ruta Bioceánica; y rutas al norte amazónico, incluyendo 
Pando y Beni.
- Un bloqueo, accidente, derrumbe, inundación, neblina intensa, conflicto social, restricción vehicular 
o demora prolongada puede significar pérdida de carga perecedera de alto valor, afectación contractual, 
riesgo sanitario, sobrecostos logísticos y pérdida de confiabilidad operativa.

ESTILO DE RESPUESTA:
- Responde siempre en español boliviano profesional.
- Sé directo, concreto y operativamente útil.
- Usa lenguaje claro, sin tecnicismos innecesarios, pero manteniendo precisión logística.
- Si hay riesgo, indícalo con urgencia apropiada.
- Incluye recomendaciones de acción cuando sea posible.
- Si el contexto no tiene información suficiente, indícalo honestamente.
- Usa emojis con moderación para mayor legibilidad, especialmente estos: 🚧 🌧️ 🚨 ✅ 📍.
- Estructura las respuestas largas con puntos, secciones claras o listas operativas.
- Prioriza la utilidad para la Torre de Control: qué ocurre, dónde ocurre, qué ruta afecta, cuál es el 
nivel de riesgo, qué impacto puede tener y qué acción se recomienda.

IMPORTANTE:
Basa tus respuestas exclusivamente en las alertas del sistema, datos internos, reportes, eventos, JSON 
del backend o contexto estructurado que se te proporcionará. No inventes información vial, no agregues 
datos externos no entregados y no supongas estados de carretera sin evidencia en el contexto recibido.

CAPACIDAD DE INTERPRETACIÓN DE DATOS Y JSON DEL BACKEND:
Debes poder revisar, leer e interpretar objetos JSON provenientes del backend del sistema. Estos JSON 
pueden contener datos sobre alertas viales, eventos, rutas, estados de carretera, niveles de riesgo, 
coordenadas, tiempos estimados, fuentes, categorías, severidad, estado de atención, historial de eventos, 
métricas operativas, reportes climáticos, tráfico, bloqueos o indicadores usados para generar gráficos 
en el frontend.

Cuando recibas JSON del backend, debes analizarlo directamente como fuente de datos textual y 
estructurada. No necesitas que se carguen imágenes, capturas ni gráficos visuales para interpretar 
la información. Si el JSON contiene datos usados para construir gráficos, tablas, mapas, indicadores, 
dashboards o series temporales, debes explicar el significado de esos gráficos únicamente a partir del 
texto y los datos contenidos en el JSON.

Por ejemplo, si el backend entrega datos agregados por ruta, severidad, fecha, departamento, tipo de 
evento o estado operativo, debes poder describir:
- Qué tendencia muestran los datos.
- Qué ruta concentra mayor riesgo.
- Qué departamento presenta más alertas.
- Qué tipo de evento es más frecuente.
- Si la situación está mejorando, empeorando o se mantiene estable.
- Qué datos parecen críticos para la operación.
- Qué acciones debería considerar la Torre de Control.

No debes decir que necesitas ver la imagen del gráfico si los datos del gráfico ya están disponibles en JSON. Tu tarea es interpretar la estructura, los campos, valores, conteos, porcentajes, categorías, fechas y relaciones contenidas en el JSON para generar una explicación clara y operativa.

CRITERIOS DE ANÁLISIS OPERATIVO:
Cuando analices una alerta vial, prioriza los siguientes elementos:
1. Ubicación exacta o aproximada del evento.
2. Ruta afectada y tramos comprometidos.
3. Tipo de evento: bloqueo, accidente, derrumbe, lluvia, neblina, inundación, mantenimiento, conflicto social, restricción u otro.
4. Severidad o nivel de riesgo, si está disponible.
5. Impacto probable en camiones frigoríficos.
6. Riesgo para la carga de cadena de frío.
7. Posible demora o afectación logística.
8. Recomendación operativa inmediata.
9. Necesidad de monitoreo, desvío, parada segura, comunicación con conductor o coordinación con cliente.
10. Nivel de confianza de la información según los datos disponibles.

FORMATO RECOMENDADO DE RESPUESTA:
Cuando exista una alerta relevante, responde preferentemente con esta estructura:

🚨 Alerta vial
📍 Ubicación:
🚚 Ruta afectada:
⚠️ Nivel de riesgo:
🧊 Impacto para cadena de frío:
📊 Interpretación de datos:
✅ Recomendación operativa:
🕒 Estado o seguimiento:

Si la situación es normal o sin alertas críticas, responde de forma breve:
✅ No se identifican alertas críticas en el contexto proporcionado.
Sin embargo, aclara si la información es limitada o si faltan datos recientes.

REGLAS DE HONESTIDAD Y LIMITACIÓN:
- Si no hay datos suficientes, dilo claramente.
- Si el JSON está incompleto, mal formado o no contiene campos relevantes, indícalo.
- Si una ruta no aparece en las alertas proporcionadas, no afirmes que está libre o transitable; 
    solo indica que no hay información disponible sobre esa ruta en el contexto recibido.
- No generes rutas alternativas si no están presentes en los datos entregados.
- No confirmes apertura, transitabilidad o cierre de carretera sin evidencia explícita.
- No inventes horarios, lugares, causas, responsables ni tiempos de normalización.
- Diferencia claramente entre dato confirmado, dato parcial y recomendación operativa.

ENFOQUE PARA TRANSFREEZER BOLIVIA S.R.L.:
Tu respuesta debe ayudar a tomar decisiones rápidas para proteger la carga, al conductor, el equipo 
frigorífico, la continuidad de la ruta y el cumplimiento con clientes. La prioridad es evitar que una 
unidad frigorífica quede detenida en una zona de riesgo, sin combustible, sin seguridad, sin conectividad 
o con amenaza de ruptura de cadena de frío.

Cuando exista riesgo alto, usa tono urgente y operativo. Cuando el riesgo sea moderado, recomienda 
monitoreo y validación antes de despacho. Cuando el riesgo sea bajo, mantén la respuesta breve y 
enfocada. Siempre que sea posible, convierte los datos en una acción concreta para la Torre de Control.

Tu objetivo final es transformar alertas, JSON, métricas y datos del backend en inteligencia vial 
clara, confiable y accionable para operaciones de transporte frigorífico en Bolivia."""



@dataclass(slots=True)
class GeminiHandle:
    model_name: str | None = None
    model: Any | None = None


class AsistenteInteligenteService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._repository = AsistenteSQLiteRepository(Path(settings.asistente_db_file))
        self._sessions: dict[str, list[ChatMessage]] = {}
        self._gemini_sessions: dict[str, Any] = {}
        self._classifier = None
        self._nlp = None
        self._gemini_handle = GeminiHandle()
        self._ready = False
        self._last_mode = '—'
        self._last_ingested_at = '—'
        # Rastreo real del estado del LLM
        self._last_llm_ok: bool | None = None   # None = no se ha intentado aún
        self._last_active_llm: str | None = None  # qué LLM respondió último

    def preload(self) -> None:
        self.ensure_ready()

    def ensure_ready(self) -> None:
        if self._ready:
            return
        self._repository.initialize_schema()
        self.refresh_knowledge_base()
        self._ready = True

    def refresh_knowledge_base(self) -> None:
        raw_records, mode = self._ingestar_datos()
        print(f'[refresh_knowledge_base] Ingesta obtuvo {len(raw_records)} registros (modo: {mode})')
        rows = []
        now_text = self._now_iso()
        for record in raw_records:
            class_result = self._clasificar_texto(record['texto'])
            categoria = str(class_result['categoria'])
            confianza_pct = float(class_result['confianza_pct'])
            ubicacion = self._extraer_ubicaciones(record['texto']) if categoria in {'Bloqueo de carretera', 'Desastre Natural/Clima', 'Accidente'} else 'N/A — Sin riesgo'
            rows.append(
                {
                    'fecha_ingesta': now_text,
                    'fuente': record['fuente'],
                    'url': record['url'],
                    'categoria': categoria,
                    'confianza_pct': confianza_pct,
                    'ubicacion': ubicacion,
                    'detalle_completo': record['texto'].strip(),
                }
            )
        print(f'[refresh_knowledge_base] Clasificadas {len(rows)} alertas, guardando en BD...')
        self._repository.replace_alerts(rows, mode=mode, ingested_at=now_text)
        count = self._repository.count_documents()
        print(f'[refresh_knowledge_base] ✓ BD actualizada. Total docs en BD: {count}')
        self._last_mode = mode
        self._last_ingested_at = now_text

    def health(self) -> HealthResponse:
        self.ensure_ready()
        documents = self._repository.count_documents()
        # llm_available refleja la realidad:
        # - Si nunca se ha llamado: True si hay al menos 1 key configurada
        # - Si hay llamadas previas: resultado real del último intento
        if self._last_llm_ok is not None:
            llm_ok = self._last_llm_ok
        else:
            import os
            has_gemini = bool(self._settings.asistente_gemini_api_key or
                             os.environ.get('GEMINI_API_KEY') or
                             os.environ.get('GOOGLE_API_KEY'))
            has_openrouter = bool(self._settings.openrouter_api_key or
                                 os.environ.get('OPENROUTER_API_KEY'))
            llm_ok = has_gemini or has_openrouter
        return HealthResponse(
            status='ok',
            llm_available=llm_ok,
            documents_indexed=documents,
            message='Asistente operativo.' if documents else 'Módulo en preparación. El motor PLN se conectará en la siguiente iteración.',
            version=_MODULE_VERSION,
        )

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.ensure_ready()

        session_id = request.session_id or self._new_session_id()
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        session_history = self._sessions[session_id]
        if request.history:
            session_history = list(request.history[-_MAX_HISTORY_TURNS:])

        user_turn = ChatMessage(role=MessageRole.USER, content=request.message, timestamp=self._now_iso())
        session_history.append(user_turn)

        answer_text, sources, tokens_used, model_name = self._chatbot_transfreezer(
            question=request.message,
            session_id=session_id,
            context_hint=request.context_hint,
            screen_context=request.screen_context,
        )

        assistant_turn = ChatMessage(role=MessageRole.ASSISTANT, content=answer_text, timestamp=self._now_iso())
        session_history.append(assistant_turn)
        self._sessions[session_id] = session_history[-_MAX_HISTORY_TURNS * 2:]

        return ChatResponse(
            answer=answer_text,
            sources=sources,
            session_id=session_id,
            tokens_used=tokens_used,
            model_name=model_name,
            metadata={
                'history_turns': len(session_history),
                'context_hint': request.context_hint,
                'screen_context_keys': sorted(list((request.screen_context or {}).keys())),
                'documents_indexed': self._repository.count_documents(),
                'last_mode': self._last_mode,
                'last_ingested_at': self._last_ingested_at,
            },
        )

    def list_sessions(self) -> SessionListResponse:
        summaries = []
        for session_id, history in self._sessions.items():
            preview = history[-1].content[:48] if history else ''
            summaries.append({'session_id': session_id, 'turns': len(history), 'preview': preview})
        return SessionListResponse(sessions=summaries, total=len(summaries))

    def get_session(self, session_id: str) -> SessionDetailResponse:
        messages = list(self._sessions.get(session_id, []))
        return SessionDetailResponse(
            session_id=session_id,
            messages=messages,
            total_turns=len(messages),
            last_updated=self._last_ingested_at,
        )

    def clear_session(self, session_id: str) -> SessionClearResponse:
        self._sessions.pop(session_id, None)
        self._gemini_sessions.pop(session_id, None)
        return SessionClearResponse(ok=True, session_id=session_id)

    def clear_all_sessions(self) -> SessionClearResponse:
        self._sessions.clear()
        self._gemini_sessions.clear()
        return SessionClearResponse(ok=True, session_id=None)

    def get_documents_count(self) -> int:
        self.ensure_ready()
        return self._repository.count_documents()

    # ------------------------------------------------------------------
    # Notebook pipeline
    # ------------------------------------------------------------------

    def _ingestar_datos(self) -> tuple[list[dict[str, str]], str]:
        datos_reales: list[dict[str, str]] = []

        for nombre, url in FUENTES.items():
            print(f'[_ingestar_datos] Scrapeando {nombre}...')
            texto = self._extraer_texto_html(url, nombre)
            if texto:
                datos_reales.append({'fuente': nombre, 'url': url, 'texto': texto})
                print(f'[_ingestar_datos]   ✓ {nombre}: OK ({len(texto)} caracteres)')
            else:
                print(f'[_ingestar_datos]   ✗ {nombre}: falló (retornó None)')

        # Retorna los datos que haya scrapeado (muchos, pocos o ninguno). Nunca usa respaldo.
        print(f'[_ingestar_datos] Total scrapeado: {len(datos_reales)} fuentes exitosas')
        return datos_reales, 'REAL'

    def _extraer_texto_html(self, url: str, fuente: str) -> str | None:
        if requests is None or BeautifulSoup is None:
            print(f'[_extraer_texto_html] {fuente}: requests o BeautifulSoup no importados')
            return None

        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )
        }
        timeout = self._settings.asistente_scrape_timeout_seconds
        print(f'[_extraer_texto_html] {fuente}: timeout={timeout}s, URL={url}')

        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            print(f'[_extraer_texto_html] {fuente}: GET OK (status {response.status_code})')
            soup = BeautifulSoup(response.text, 'html.parser')

            # Limpiamos basura, marquesinas (marquee) y menús
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'meta', 'link', 'noscript', 'iframe', 'button', 'form', 'marquee']):
                tag.decompose()

            # Estrategia por fuente
            texto_final = ""
            if 'SENAMHI' in fuente.upper():
                # El SENAMHI usa tablas para sus alertas o divs específicos.
                # Ignoramos puros spans que suelen ser menús repetitivos.
                elementos = soup.find_all(['table', 'div', 'p'], class_=lambda c: c and 'alerta' in c.lower())
                if not elementos: # Fallback si no tienen clase alerta
                    elementos = soup.find_all(['td', 'article', 'h1', 'h2', 'p'])
            else:
                elementos = soup.find_all(['p', 'h1', 'h2', 'h3', 'article', 'li', 'span', 'div', 'td'])

            texto_crudo = ' '.join(elemento.get_text(separator=' ', strip=True) for elemento in elementos)
            texto = re.sub(r'\s+', ' ', texto_crudo).strip()
            
            # Filtramos si el texto es solo "Sistema de alerta hidrologica" repetido
            if 'Sistema de alerta temprana hidrológica' in texto and len(set(texto.split())) < 10:
                return None

            umbral_minimo = 60 if 'SENAMHI' in fuente.upper() else 150
            if len(texto) < umbral_minimo:
                print(f'[_extraer_texto_html] {fuente}: texto muy corto ({len(texto)} < {umbral_minimo})')
                return None
            print(f'[_extraer_texto_html] {fuente}: texto OK ({len(texto)} caracteres, umbral={umbral_minimo})')
            return texto[:3000]
        except Exception as e:
            print(f'[_extraer_texto_html] {fuente}: EXCEPCIÓN: {type(e).__name__}: {str(e)}')
            return None

    def _clasificar_texto(self, texto: str) -> dict[str, Any]:
        pipeline_model = self._ensure_classifier()
        if pipeline_model is not None:
            resultado = pipeline_model(
                texto[:_ZERO_SHOT_MAX_CHARS],
                candidate_labels=ETIQUETAS_RIESGO,
                hypothesis_template='Este texto informa sobre {}.',
            )
            labels = list(resultado['labels'])
            scores = [float(score) for score in resultado['scores']]
            return {
                'categoria': labels[0],
                'confianza_pct': round(scores[0] * 100, 2),
                'scores_completos': dict(zip(labels, [round(score * 100, 2) for score in scores])),
            }

        texto_lower = texto.lower()
        keyword_map = [
            (('bloqueo', 'bloquean', 'cerrado', 'cerrada', 'cortada', 'corte', 'desvío', 'desvio'), 'Bloqueo de carretera'),
            (('lluvia', 'nevada', 'granizada', 'alerta', 'senamhi', 'tormenta', 'inundacion', 'inundación', 'hielo', 'riada', 'deslizamiento'), 'Desastre Natural/Clima'),
            (('accidente', 'volcadura', 'choque', 'colision', 'colisión'), 'Accidente'),
        ]
        for keywords, category in keyword_map:
            if any(keyword in texto_lower for keyword in keywords):
                return {'categoria': category, 'confianza_pct': 72.0, 'scores_completos': {category: 72.0}}
        return {'categoria': 'Tránsito Normal', 'confianza_pct': 61.0, 'scores_completos': {'Tránsito Normal': 61.0}}

    def _extraer_ubicaciones(self, texto: str) -> str:
        ubicaciones_ner: list[str] = []

        nlp_model = self._ensure_nlp()
        if nlp_model is not None:
            doc = nlp_model(texto[:_NER_MAX_CHARS])
            ubicaciones_ner = [
                ent.text.strip()
                for ent in doc.ents
                if ent.label_ in ('LOC', 'GPE') and len(ent.text.strip()) > 2
            ]

        toponimos_encontrados = [top for top in TOPONIMOS_BOLIVIA if top.lower() in texto.lower() and top not in ubicaciones_ner]
        todas = ubicaciones_ner + toponimos_encontrados
        unicas = list(dict.fromkeys(todas))[:6]
        return ' | '.join(unicas) if unicas else 'No especificada'

    def _recuperar_alertas_relevantes(self, question: str, max_alertas: int = _MAX_CONTEXT_ALERTS) -> list[dict[str, Any]]:
        pregunta = question.lower()
        print(f'[_recuperar_alertas_relevantes] Pregunta: "{question}"')
        category_rules = {
            ('bloqueo', 'bloqueos', 'cortada', 'cortado', 'cerrada', 'cerrado'): 'Bloqueo de carretera',
            ('clima', 'lluvia', 'nevada', 'alerta', 'senamhi', 'tormenta', 'inundacion', 'inundación', 'hielo', 'graniz'): 'Desastre Natural/Clima',
            ('accidente', 'volcadura', 'choque', 'colision', 'colisión'): 'Accidente',
            ('normal', 'libre', 'sin problemas', 'transitable'): 'Tránsito Normal',
        }

        for keywords, category in category_rules.items():
            if any(keyword in pregunta for keyword in keywords):
                print(f'[_recuperar_alertas_relevantes] Detectada categoría: {category}')
                records = self._repository.search_by_category(category, limit=max_alertas)
                print(f'[_recuperar_alertas_relevantes]   Encontradas {len(records)} alerta(s) por categoría')
                if records:
                    return records

        palabras_lugar = [
            palabra.strip('¿?.,!"()')
            for palabra in question.split()
            if len(palabra) > 3 and (palabra[0].isupper() or palabra.lower() in [
                'yapacani', 'yapacaní', 'sillar', 'caranavi', 'coroico', 'cochabamba',
                'santa cruz', 'oruro', 'potosi', 'potosí', 'pando', 'beni', 'tarija',
                'la paz', 'pazña', 'pazna', 'trinidad', 'cobija', 'bermejo', 'yungas', 'bioceánica'
            ])
        ]
        for lugar in palabras_lugar:
            records = self._repository.search_by_location(lugar, limit=max_alertas)
            if records:
                return records

        stopwords = {
            'que', 'cual', 'como', 'donde', 'cuales', 'sobre', 'para', 'esta', 'está',
            'algún', 'alguna', 'tiene', 'existe', 'información', 'informacion', 'dame', 'dime', 'puedes',
        }
        palabras_busqueda = [palabra for palabra in pregunta.split() if len(palabra) > 4 and palabra not in stopwords]
        if palabras_busqueda:
            print(f'[_recuperar_alertas_relevantes] Buscando por keywords: {palabras_busqueda}')
            records = self._repository.search_by_keywords(palabras_busqueda, limit=max_alertas)
            print(f'[_recuperar_alertas_relevantes]   Encontradas {len(records)} alerta(s) por keywords')
            if records:
                return records

        print(f'[_recuperar_alertas_relevantes] Retornando alertas activas (fallback genérico)')
        all_alerts = self._repository.fetch_active_alerts(limit=max_alertas)
        print(f'[_recuperar_alertas_relevantes] Total alertas activas: {len(all_alerts)}')
        return all_alerts

    def _construir_contexto_para_gemini(self, rows: list[dict[str, Any]]) -> str:
        if not rows:
            return '[No se encontraron alertas activas en el sistema en este momento.]'

        lineas = ['=== ALERTAS ACTIVAS DEL SISTEMA ===']
        for row in rows:
            lineas.append(
                f"\n--- ALERTA #{row['id']} ---\n"
                f"Fecha de ingesta: {row['fecha_ingesta']}\n"
                f"Fuente:           {row['fuente']}\n"
                f"Categoría:        {row['categoria']}\n"
                f"Confianza IA:     {row['confianza_pct']}%\n"
                f"Ubicación NER:    {row['ubicacion']}\n"
                f"Detalle completo: {row['detalle_completo']}"
            )
        lineas.append('\n=== FIN DE ALERTAS ===')
        return '\n'.join(lineas)

    def _chatbot_transfreezer(
        self,
        question: str,
        session_id: str,
        context_hint: str | None,
        screen_context: dict[str, Any] | None,
    ) -> tuple[str, list[CitedSource], int | None, str | None]:
        rows = self._recuperar_alertas_relevantes(question)
        context = self._construir_contexto_para_gemini(rows)
        screen_context_block = self._formatear_contexto_pantalla(screen_context)

        # Prompt único con system context incluido → 1 sola llamada API, sin warm-up de sesión
        prompt_final = (
            f'{SYSTEM_PROMPT_GEMINI}\n\n'
            '---\n'
            'CONTEXTO DE ALERTAS DEL SISTEMA TRANSFREEZER:\n'
            f'{context}\n\n'
            f'{screen_context_block}\n\n'
            f'PREGUNTA DEL OPERADOR: {question}\n\n'
            'Responde de forma clara, concisa y operativamente útil basándote '
            'estrictamente en el contexto proporcionado. '
            'Si hay contexto de pantalla, prioriza explicar lo que el usuario '
            'está viendo en su módulo actual sin inventar valores.'
        )

        sources = [self._row_to_source(row) for row in rows]
        tokens_used: int | None = None

        # ── Intento 1: Gemini (generate_content directo, 1 sola request) ──
        model = self._ensure_gemini_model()
        if model is not None:
            try:
                response = model.generate_content(prompt_final)
                answer_text = getattr(response, 'text', '') or '—'
                model_name = self._gemini_handle.model_name
                usage_metadata = getattr(response, 'usage_metadata', None)
                if usage_metadata is not None:
                    tokens_used = int(getattr(usage_metadata, 'total_token_count', 0) or 0) or None
                self._last_llm_ok = True
                self._last_active_llm = 'gemini'
                return answer_text, sources, tokens_used, model_name
            except Exception as exc:
                print(f'[AsistenteService] Gemini falló, intentando OpenRouter. Error: {exc}')

        # ── Intento 2: OpenRouter (Llama 3.3 70B free) ──
        openrouter_answer = self._call_openrouter(prompt_final)
        if openrouter_answer is not None:
            self._last_llm_ok = True
            self._last_active_llm = 'openrouter'
            return openrouter_answer, sources, None, self._settings.openrouter_model

        # ── Ambos LLMs fallaron ──
        self._last_llm_ok = False
        return (
            f"[MODO FALLBACK — LLM no disponible]\nSe encontraron {len(rows)} alerta(s) relevantes. "
            "Gemini y OpenRouter no respondieron en este momento.",
            sources,
            None,
            None,
        )

    def _formatear_contexto_pantalla(self, screen_context: dict[str, Any] | None) -> str:
        if not screen_context:
            return '[CONTEXTO DE PANTALLA: no recibido]'

        lines: list[str] = ['=== CONTEXTO DE PANTALLA ACTUAL (ENVIADO POR FRONTEND) ===']

        module_name = str(screen_context.get('module', '')).strip()
        route_name = str(screen_context.get('route', '')).strip()
        page_title = str(screen_context.get('page_title', '')).strip()
        summary = str(screen_context.get('visible_summary', '')).strip()

        if module_name:
            lines.append(f'Módulo activo: {module_name}')
        if route_name:
            lines.append(f'Ruta: {route_name}')
        if page_title:
            lines.append(f'Título de página: {page_title}')
        if summary:
            lines.append(f'Resumen visible: {summary[:1200]}')

        filters_obj = screen_context.get('filters')
        if isinstance(filters_obj, dict) and filters_obj:
            lines.append('Filtros visibles:')
            for key, value in list(filters_obj.items())[:20]:
                lines.append(f'- {key}: {value}')

        kpis_obj = screen_context.get('kpis')
        if isinstance(kpis_obj, list) and kpis_obj:
            lines.append('KPIs visibles:')
            for kpi in kpis_obj[:20]:
                if isinstance(kpi, dict):
                    label = str(kpi.get('label', 'KPI'))
                    value = str(kpi.get('value', 'N/D'))
                    trend = str(kpi.get('trend', '')).strip()
                    trend_part = f' ({trend})' if trend else ''
                    lines.append(f'- {label}: {value}{trend_part}')

        table_rows = screen_context.get('table_preview')
        if isinstance(table_rows, list) and table_rows:
            lines.append('Muestra de tabla visible:')
            for row in table_rows[:8]:
                lines.append(f'- {row}')

        lines.append('=== FIN CONTEXTO DE PANTALLA ===')
        return '\n'.join(lines)

    def _row_to_source(self, row: dict[str, Any]) -> CitedSource:
        fuente = str(row.get('fuente', 'Fuente desconocida'))
        source_type = SourceType.DOCUMENT if ('ABC' in fuente or 'SENAMHI' in fuente) else SourceType.REPORT
        return CitedSource(
            type=source_type,
            title=f"{fuente} — {row.get('categoria', 'sin categoría')}",
            excerpt=str(row.get('detalle_completo', ''))[:240],
            confidence=min(float(row.get('confianza_pct', 0.0)) / 100.0, 1.0),
        )

    def _ensure_classifier(self):
        if self._classifier is not None:
            return self._classifier
        if pipeline is None:
            return None
        try:
            self._classifier = pipeline('zero-shot-classification', model=self._settings.asistente_zero_shot_model)
        except Exception:
            self._classifier = None
        return self._classifier

    def _ensure_nlp(self):
        if self._nlp is not None:
            return self._nlp
        if spacy is None:
            return None
        try:
            self._nlp = spacy.load('es_core_news_sm')
        except Exception:
            self._nlp = None
        return self._nlp

    def _ensure_gemini_model(self):
        if self._gemini_handle.model is not None:
            return self._gemini_handle.model
        if genai is None:
            return None

        api_key = self._settings.asistente_gemini_api_key or self._get_env_api_key()
        if not api_key:
            return None

        try:
            genai.configure(api_key=api_key)
        except Exception:
            return None

        for model_name in self._settings.asistente_gemini_models or MODELOS_FALLBACK:
            try:
                model = genai.GenerativeModel(model_name)
                # No hacemos ping — el modelo se valida en el primer uso real.
                # Un ping aquí causa rate-limiting y falsos negativos en el health check.
                self._gemini_handle = GeminiHandle(model_name=model_name, model=model)
                return model
            except Exception:
                continue

        return None

    def _call_openrouter(self, prompt: str) -> str | None:
        """Llama a OpenRouter iterando modelos gratuitos hasta que uno responda."""
        import os
        if requests is None:
            return None

        api_key = (
            self._settings.openrouter_api_key
            or os.environ.get('OPENROUTER_API_KEY', '')
        )
        if not api_key:
            return None

        # Intentar en orden: modelo configurado primero, luego fallbacks
        models_to_try = (
            self._settings.openrouter_model_fallbacks
            or [self._settings.openrouter_model, 'google/gemma-4-31b-it:free', 'meta-llama/llama-3.3-70b-instruct:free']
        )

        or_headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://transfreezer.bo',
            'X-Title': 'TransFreezer Insight Suite',
        }

        for model in models_to_try:
            try:
                resp = requests.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers=or_headers,
                    json={
                        'model': model,
                        'messages': [{'role': 'user', 'content': prompt}],
                        'max_tokens': 1024,
                    },
                    timeout=30,
                )
                if resp.ok:
                    data = resp.json()
                    answer = data['choices'][0]['message']['content']
                    print(f'[AsistenteService] OpenRouter respondió con: {model}')
                    return answer
                else:
                    print(f'[AsistenteService] OpenRouter [{model}] falló {resp.status_code}, probando siguiente...')
                    continue
            except Exception as exc:
                print(f'[AsistenteService] OpenRouter [{model}] error: {exc}')
                continue

        return None

    def _get_or_create_gemini_session(self, session_id: str):
        model = self._ensure_gemini_model()
        if model is None:
            return None
        if session_id in self._gemini_sessions:
            return self._gemini_sessions[session_id]

        try:
            chat_session = model.start_chat(history=[])
            try:
                chat_session.send_message(
                    f"[INSTRUCCIONES DE SISTEMA]\n{SYSTEM_PROMPT_GEMINI}\n"
                    "Responde 'Listo para asistir a la Torre de Control de TransFreezer Bolivia.' cuando hayas procesado estas instrucciones."
                )
            except Exception:
                pass
            self._gemini_sessions[session_id] = chat_session
            return chat_session
        except Exception:
            return None

    def _get_env_api_key(self) -> str:
        import os

        return (
            os.environ.get('GEMINI_API_KEY', '')
            or os.environ.get('GOOGLE_API_KEY', '')
            or os.environ.get('ASISTENTE_GEMINI_API_KEY', '')
        )

    @staticmethod
    def _new_session_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


_service: AsistenteInteligenteService | None = None


def get_asistente_service(settings: Settings) -> AsistenteInteligenteService:
    global _service
    if _service is None:
        _service = AsistenteInteligenteService(settings)
    return _service
