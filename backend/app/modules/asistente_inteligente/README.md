# Asistente Inteligente (PLN)

Nombre técnico interno: `asistente_inteligente`.  
Nombre comercial visible: **Asistente Inteligente (PLN)**

## Estado actual

- **Stub operativo**: los endpoints están registrados y responden, pero el motor LLM no está conectado.
- La UI del frontend muestra la interfaz de chat completa; las respuestas son mensajes de preparación.

## Arquitectura del módulo

```
asistente_inteligente/
├── controllers/
│   └── asistente_controller.py   # Thin router FastAPI (health, chat, sessions)
├── schemas/
│   └── asistente_schema.py       # Pydantic: ChatRequest, ChatResponse, HealthResponse, etc.
├── services/
│   └── asistente_service.py      # Lógica: sesiones, historial, llamada al LLM (stub)
└── README.md                     # Este archivo
```

## Endpoints disponibles

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/v1/asistente-inteligente/health` | Estado del módulo y disponibilidad del LLM |
| `POST` | `/api/v1/asistente-inteligente/chat` | Enviar un mensaje y recibir respuesta |
| `GET` | `/api/v1/asistente-inteligente/sessions` | Listar sesiones activas |
| `DELETE` | `/api/v1/asistente-inteligente/sessions/{id}` | Eliminar una sesión concreta |
| `DELETE` | `/api/v1/asistente-inteligente/sessions` | Eliminar todas las sesiones |

## Contrato de la API de chat

### Request `POST /chat`
```json
{
  "message": "¿Cuáles son los contratos con mayor riesgo este ciclo?",
  "history": [
    { "role": "user", "content": "Hola", "timestamp": "2026-04-27T18:00:00Z" },
    { "role": "assistant", "content": "¡Hola! ¿En qué puedo ayudarte?", "timestamp": "2026-04-27T18:00:01Z" }
  ],
  "context_hint": "torre-control-sio",
  "session_id": "abc-123-..."
}
```

### Response
```json
{
  "answer": "Texto de respuesta en Markdown...",
  "sources": [
    { "type": "document", "title": "Contrato Ruta SUR-2", "excerpt": "...", "confidence": 0.92 }
  ],
  "session_id": "abc-123-...",
  "tokens_used": 512,
  "model_name": "gemini-2.0-flash",
  "metadata": {}
}
```

## Plan de migración (cuando se conecte el motor LLM)

1. **Elegir motor**: Gemini API, OpenAI, Claude API o modelo local (Ollama).
2. **Añadir credencial** en `Settings` (`asistente_api_key`, `asistente_model_name`).
3. **Reemplazar `_call_llm()`** en `asistente_service.py` con la llamada real.
4. **Indexar documentos**: crear un `DocumentRepository` con embeddings + vector store.
5. **Reemplazar `_retrieve_sources()`** con el retriever RAG.
6. **Opcional**: mover el store de sesiones de in-memory a Redis para persistencia.

## Propósito previsto

- Leer y resumir documentos operativos (manuales, contratos, reportes de mermas).
- Buscar conocimiento en reportes y criterios internos de TransFreezer.
- Responder consultas del usuario con contexto del ciclo activo de la Torre de Control SIO.
- Analizar cláusulas de contratos y generar alertas presupuestarias contextualizadas.
