"""
Rutas proxy para reenviar peticiones a GLPI.
Maneja todas las peticiones hacia endpoints de GLPI.
"""
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request, Response, HTTPException, status, Header
from starlette.responses import JSONResponse, PlainTextResponse

from app.config import get_settings
from app.services.glpi_client import glpi_client
from app.services.oauth import oauth_manager
from app.services.logger import proxy_logger


import json as _json

DEFAULT_OBSERVER_USER_ID = 7  # HaraiDasan

router = APIRouter(prefix="/api/v2.2", tags=["Proxy"])


async def _add_default_observer(ticket_id: int, headers: Dict[str, str]):
    """Adds HaraiDasan as observer to every newly created ticket."""
    await glpi_client.request(
        method="POST",
        endpoint=f"/api.php/v2.2/Assistance/Ticket/{ticket_id}/TeamMember",
        json_data={"type": "User", "id": DEFAULT_OBSERVER_USER_ID, "role": "observer"},
        headers=headers
    )




async def _extract_request_body(request: Request) -> Optional[bytes]:
    """Extrae el body de la petición."""
    if hasattr(request, "_body") and request._body:
        return request._body

    body = await request.body()
    if body:
        request._body = body
    return body


async def _proxify_request(
    method: str,
    resource: str,
    request: Request,
    authorization: Optional[str] = Header(None)
) -> Response:
    """
    Reenvía una petición a GLPI y retorna la respuesta.

    Args:
        method: Método HTTP
        resource: Path del recurso (ej: Administration/User)
        request: Objeto Request de FastAPI
        authorization: Header Authorization

    Returns:
        Response de FastAPI
    """
    # Generar ID de request
    request_id = str(uuid.uuid4())

    # Construir endpoint
    endpoint = f"/api.php/v2.2/{resource}"

    # Obtener query params
    query_params = dict(request.query_params)

    # Headers adicionales del cliente
    FORWARDED_HEADERS = {"glpi-entity", "glpi-profile", "glpi-entity-recursive", "accept-language"}
    client_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() in FORWARDED_HEADERS
    }
    if authorization:
        client_headers["Authorization"] = authorization

    # Obtener body
    body = await _extract_request_body(request)
    json_data = None
    form_data = None

    if body:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            import json
            try:
                json_data = json.loads(body)
            except:
                pass
        elif "application/x-www-form-urlencoded" in content_type:
            form_data = body

    # Medir tiempo
    start_time = time.time()

    # Registrar request hacia GLPI
    proxy_logger.log_upstream_request(
        request_id=request_id,
        method=method,
        url=f"{get_settings().glpi_api_url}{endpoint}",
        headers={**dict(request.headers), **client_headers},
        body=json_data or form_data
    )

    # Realizar petición a GLPI
    try:
        response = await glpi_client.request(
            method=method,
            endpoint=endpoint,
            params=query_params,
            json_data=json_data,
            data=form_data,
            headers=client_headers or None
        )

        # Calcular tiempo de respuesta
        response_time_ms = int((time.time() - start_time) * 1000)

        # Registrar respuesta de GLPI
        proxy_logger.log_upstream_response(
            request_id=request_id,
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.text,
            response_time_ms=response_time_ms
        )

        # Auto-add default observer on ticket creation
        if method == "POST" and resource == "Assistance/Ticket" and response.status_code in (200, 201):
            try:
                ticket_id = _json.loads(response.content).get("id")
                if ticket_id:
                    await _add_default_observer(ticket_id, {"Authorization": authorization})
            except Exception:
                pass

        # Construir respuesta
        headers = dict(response.headers)
        # Limpiar headers problemáticos
        headers.pop("content-encoding", None)
        headers.pop("transfer-encoding", None)

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=headers,
            media_type=response.headers.get("content-type", "application/json")
        )

    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)

        # Registrar error
        proxy_logger.log_upstream_response(
            request_id=request_id,
            status_code=502,
            headers={},
            body=str(e),
            response_time_ms=response_time_ms
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al comunicarse con GLPI: {str(e)}"
        )


# Definir rutas proxy genéricas
@router.api_route("/{resource:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_handler(
    resource: str,
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Proxy genérico para todos los endpoints de GLPI.

    Este endpoint reenvía todas las peticiones a GLPI manteniendo
    el método HTTP, headers y body originales.

    Args:
        resource: Path del recurso (ej: Administration/User)
        request: Objeto Request de FastAPI
        authorization: Header Authorization (Bearer token)

    Returns:
        Respuesta de GLPI
    """
    # Verificar que el recurso no sea un endpoint especial
    if resource in ("token", "Health", "ping", "logs"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint no encontrado"
        )

    # Verificar que hay token de acceso
    if not authorization or not authorization.startswith("Bearer "):
        # Intentar usar token cacheado
        cached_token = oauth_manager.get_cached_token()
        if cached_token:
            authorization = f"Bearer {cached_token}"
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Se requiere token de acceso"
            )

    return await _proxify_request(
        method=request.method,
        resource=resource,
        request=request,
        authorization=authorization
    )