"""
Middleware de logging para FastAPI.
Captura y registra todas las peticiones de entrada y respuestas de salida.
"""
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.logger import proxy_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging de requests y responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Procesa la petición y registra información de entrada y salida.

        Args:
            request: Petición de FastAPI
            call_next: Siguiente middleware/handler

        Returns:
            Response
        """
        # Generar ID único para esta petición
        request_id = str(uuid.uuid4())

        # Obtener información de la petición
        method = request.method
        path = request.url.path
        source_ip = request.client.host if request.client else None
        headers = dict(request.headers)

        # Capturar body de la petición si existe
        body = None
        if method in ("POST", "PUT", "PATCH"):
            # Leer el body para logging (reutilizable después)
            body = await request.body()
            # Recrear el request con el body
            request._body = body

        # Registrar petición de entrada (input)
        proxy_logger.log_request(
            method=method,
            path=path,
            headers=headers,
            body=body.decode("utf-8") if body else None,
            direction="client_to_proxy",
            source_ip=source_ip
        )

        # Medir tiempo de respuesta
        start_time = time.time()

        # Procesar la petición
        response = await call_next(request)

        # Calcular tiempo de respuesta
        response_time_ms = int((time.time() - start_time) * 1000)

        # Obtener body de la respuesta
        response_body = None
        if hasattr(response, "body"):
            response_body = response.body

        # Registrar respuesta de salida (output)
        proxy_logger.log_response(
            request_id=request_id,
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response_body.decode("utf-8") if response_body else None,
            response_time_ms=response_time_ms,
            direction="proxy_to_client"
        )

        # Agregar request_id a los headers de respuesta
        response.headers["X-Request-ID"] = request_id

        return response