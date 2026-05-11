"""
Schemas para el módulo Asistente Inteligente (PLN).

Estructura preparada para conectar con el motor de PLN/LLM cuando se migre
la implementación existente. Los tipos aquí definen el contrato de la API
sin acoplar nada al modelo subyacente.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Tipos auxiliares
# ---------------------------------------------------------------------------

class MessageRole(str, Enum):
    """Rol de cada turno de conversación."""
    USER = 'user'
    ASSISTANT = 'assistant'
    SYSTEM = 'system'


class SourceType(str, Enum):
    """Tipo de fuente que el asistente puede citar."""
    DOCUMENT = 'document'
    REPORT = 'report'
    MANUAL = 'manual'
    KNOWLEDGE_BASE = 'knowledge_base'
    UNKNOWN = 'unknown'


# ---------------------------------------------------------------------------
# Mensajes y turnos de conversación
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """Un único turno de conversación (usuario o asistente)."""
    role: MessageRole
    content: str = Field(..., min_length=1, max_length=32_000)
    timestamp: str | None = Field(
        default=None,
        description='ISO 8601 timestamp del mensaje. El backend lo asigna si no se envía.'
    )


class CitedSource(BaseModel):
    """Fuente citada por el asistente en su respuesta."""
    type: SourceType = SourceType.UNKNOWN
    title: str
    excerpt: str | None = None
    page: int | None = None
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description='Puntuación de relevancia entre 0 y 1.'
    )


# ---------------------------------------------------------------------------
# Request / Response de la API
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """
    Cuerpo de la solicitud POST /chat.

    El campo `history` contiene los turnos anteriores de la conversación
    para que el LLM mantenga contexto. El campo `message` es el turno
    nuevo del usuario.
    """
    message: str = Field(..., min_length=1, max_length=4_000, description='Mensaje del usuario.')
    history: list[ChatMessage] = Field(
        default_factory=list,
        description='Historial de la conversación (hasta N turnos previos).'
    )
    context_hint: str | None = Field(
        default=None,
        description='Pista opcional de contexto (módulo activo, filtros, etc.).'
    )
    screen_context: dict[str, Any] = Field(
        default_factory=dict,
        description='Contexto visible de la pantalla actual (KPIs, filtros, tablas, resumen textual).'
    )
    session_id: str | None = Field(
        default=None,
        description='ID de sesión para asociar la conversación en el backend.'
    )


class ChatResponse(BaseModel):
    """
    Respuesta del asistente tras procesar el mensaje.

    El campo `answer` es la respuesta en texto plano o Markdown.
    El campo `sources` lista las fuentes citadas si el backend las provee.
    El campo `session_id` puede ser emitido o actualizado por el backend.
    """
    answer: str
    sources: list[CitedSource] = Field(default_factory=list)
    session_id: str | None = None
    tokens_used: int | None = Field(
        default=None,
        description='Tokens consumidos (útil para monitoreo de costos).'
    )
    model_name: str | None = Field(
        default=None,
        description='Nombre del modelo LLM que generó la respuesta.'
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description='Metadatos adicionales (latencia, versión del prompt, etc.).'
    )


class HealthResponse(BaseModel):
    """Estado operativo del servicio del asistente."""
    status: str = 'ok'
    llm_available: bool = False
    documents_indexed: int = 0
    message: str = 'Módulo en preparación. El motor PLN se conectará en la siguiente iteración.'
    version: str = '0.1.0-stub'


class SessionListResponse(BaseModel):
    """Lista resumida de sesiones de conversación disponibles."""
    sessions: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class SessionDetailResponse(BaseModel):
    """Detalle de una sesión completa con su historial de mensajes."""
    session_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    total_turns: int = 0
    last_updated: str = '—'


class SessionClearResponse(BaseModel):
    """Confirmación de limpieza de sesión."""
    ok: bool = True
    session_id: str | None = None
