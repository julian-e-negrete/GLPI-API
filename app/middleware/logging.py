"""
Middleware de logging para FastAPI.
Captura y registra todas las peticiones de entrada y respuestas de salida.
"""
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from app.services.logger import proxy_logger


class LoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())

        # Capturar body del request
        body = None
        if request.method in ("POST", "PUT", "PATCH"):
            body = await request.body()
            request._body = body

        proxy_logger.log_request(
            method=request.method,
            path=request.url.path,
            headers=dict(request.headers),
            body=body.decode("utf-8") if body else None,
            direction="client_to_proxy",
            source_ip=request.client.host if request.client else None,
            request_id=request_id
        )

        start_time = time.time()
        response = await call_next(request)
        response_time_ms = int((time.time() - start_time) * 1000)

        # Consumir el stream para capturar el body de la respuesta
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk if isinstance(chunk, bytes) else chunk.encode()

        proxy_logger.log_response(
            request_id=request_id,
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response_body.decode("utf-8", errors="replace") if response_body else None,
            response_time_ms=response_time_ms,
            direction="proxy_to_client"
        )

        # Reconstruir la respuesta con el body ya consumido
        rebuilt = StarletteResponse(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )
        rebuilt.headers["X-Request-ID"] = request_id
        return rebuilt
