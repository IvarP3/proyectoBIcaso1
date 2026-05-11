"""
Controller (router FastAPI) para el módulo Asistente Inteligente (PLN).

Expone los endpoints necesarios para que el frontend pueda:
  - Verificar el estado del módulo (GET /health)
  - Enviar un mensaje de chat (POST /chat)
  - Listar sesiones activas (GET /sessions)
  - Limpiar una sesión concreta (DELETE /sessions/{session_id})
  - Limpiar todas las sesiones (DELETE /sessions)

Patrón idéntico al resto de módulos: thin controller → service.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.modules.asistente_inteligente.schemas.asistente_schema import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    SessionDetailResponse,
    SessionClearResponse,
    SessionListResponse,
)
from app.modules.asistente_inteligente.services.asistente_service import (
    AsistenteInteligenteService,
    get_asistente_service,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_service(settings: Settings = Depends(get_settings)) -> AsistenteInteligenteService:
    return get_asistente_service(settings)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get('/health', response_model=HealthResponse, summary='Estado del módulo')
def health_check(service: AsistenteInteligenteService = Depends(get_service)) -> HealthResponse:
    """
    Verifica si el motor PLN está disponible y cuántos documentos hay indexados.
    El frontend usa este endpoint para mostrar el estado en la UI.
    """
    return service.health()


@router.post('/chat', response_model=ChatResponse, summary='Enviar mensaje al asistente')
def chat(
    request: ChatRequest,
    service: AsistenteInteligenteService = Depends(get_service),
) -> ChatResponse:
    """
    Procesa un turno de conversación.

    El cliente envía el historial completo de la sesión junto con el
    mensaje nuevo. El servicio se encarga de gestionar el contexto y
    llamar al motor LLM (stub por ahora).
    """
    return service.chat(request)


@router.get('/sessions', response_model=SessionListResponse, summary='Listar sesiones activas')
def list_sessions(service: AsistenteInteligenteService = Depends(get_service)) -> SessionListResponse:
    """Devuelve un listado de los IDs de sesión activos y el tamaño de su historial."""
    return service.list_sessions()


@router.get('/sessions/{session_id}', response_model=SessionDetailResponse, summary='Detalle de una sesión')
def get_session(
    session_id: str,
    service: AsistenteInteligenteService = Depends(get_service),
) -> SessionDetailResponse:
    """Recupera el historial completo de una sesión concreta."""
    return service.get_session(session_id)


@router.delete(
    '/sessions/{session_id}',
    response_model=SessionClearResponse,
    summary='Eliminar una sesión',
)
def clear_session(
    session_id: str,
    service: AsistenteInteligenteService = Depends(get_service),
) -> SessionClearResponse:
    """Elimina el historial de la sesión indicada."""
    return service.clear_session(session_id)


@router.delete('/sessions', response_model=SessionClearResponse, summary='Eliminar todas las sesiones')
def clear_all_sessions(service: AsistenteInteligenteService = Depends(get_service)) -> SessionClearResponse:
    """Vacía todas las sesiones activas."""
    return service.clear_all_sessions()
