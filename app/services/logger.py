"""
Sistema de logging para el Proxy GLPI.
Guarda información de requests y responses en formato JSON.
"""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from logging.handlers import TimedRotatingFileHandler

from pythonjsonlogger import jsonlogger

from app.config import get_settings


class ProxyLogger:
    """Sistema de logging para el Proxy GLPI."""

    def __init__(self):
        self.settings = get_settings()
        self._setup_logging()

    def _setup_logging(self):
        """Configura el sistema de logging."""
        # Asegurar que existe el directorio de logs
        log_dir = self.settings.ensure_log_dir()

        # Configurar logger principal
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.settings.log_level.upper()))

        # Evitar duplicar handlers
        if root_logger.handlers:
            root_logger.handlers.clear()

        # Handler para logs de aplicación (texto)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # Handler para logs de requests (JSON)
        log_file = log_dir / "requests.jsonl"
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file),
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)

        # Formato JSON
        json_formatter = jsonlogger.JsonFormatter(
            fmt='%(timestamp)s %(level)s %(message)s',
            rename_fields={'levelname': 'level'}
        )
        file_handler.setFormatter(json_formatter)

        # Agregar nombre de logger específico
        self.logger = logging.getLogger("glpi_proxy.requests")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)

        # Logger para errores
        self.error_logger = logging.getLogger("glpi_proxy.errors")

        logging.info(f"Logging configurado. Directorio: {log_dir}")

    def _mask_sensitive_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Enmascara headers sensibles para no registrar passwords o secrets.

        Args:
            headers: Headers originales

        Returns:
            Headers con datos sensibles enmascarados
        """
        sensitive_keys = {
            'authorization', 'x-api-key', 'access_token', 'refresh_token'
        }
        always_mask = {'password', 'client_secret'}

        masked = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in always_mask:
                masked[key] = "***"
            elif key_lower in sensitive_keys:
                if value and len(value) > 10:
                    # Mantener primeros 10 caracteres
                    masked[key] = value[:10] + "***"
                else:
                    masked[key] = "***"
            else:
                masked[key] = value

        return masked

    def log_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Any = None,
        direction: str = "client_to_proxy",
        source_ip: Optional[str] = None
    ) -> str:
        """
        Registra una petición de entrada (input).

        Args:
            method: Método HTTP
            path: Path del endpoint
            headers: Headers de la petición
            body: Body de la petición
            direction: Dirección del flujo
            source_ip: IP origen

        Returns:
            ID de la petición
        """
        request_id = str(uuid.uuid4())

        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
            "type": "input",
            "direction": direction,
            "method": method,
            "path": path,
            "headers": self._mask_sensitive_headers(headers),
            "body": body,
            "source_ip": source_ip
        }

        self.logger.info(json.dumps(log_entry))
        return request_id

    def log_response(
        self,
        request_id: str,
        status_code: int,
        headers: Dict[str, str],
        body: Any = None,
        response_time_ms: Optional[int] = None,
        direction: str = "proxy_to_client",
        error: Optional[str] = None
    ):
        """
        Registra una respuesta (output).

        Args:
            request_id: ID de la petición original
            status_code: Código de estado HTTP
            headers: Headers de la respuesta
            body: Body de la respuesta
            response_time_ms: Tiempo de respuesta en milisegundos
            direction: Dirección del flujo
            error: Mensaje de error si existe
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
            "type": "output" if not error else "error",
            "direction": direction,
            "status_code": status_code,
            "headers": self._mask_sensitive_headers(headers),
            "body": body,
            "response_time_ms": response_time_ms,
            "error": error
        }

        if error:
            self.error_logger.error(json.dumps(log_entry))
        else:
            self.logger.info(json.dumps(log_entry))

    def log_upstream_request(
        self,
        request_id: str,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Any = None
    ):
        """
        Registra una petición hacia GLPI (upstream).

        Args:
            request_id: ID de la petición original
            method: Método HTTP
            url: URL completa
            headers: Headers de la petición
            body: Body de la petición
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
            "type": "input",
            "direction": "proxy_to_glpi",
            "method": method,
            "path": url,
            "headers": self._mask_sensitive_headers(headers),
            "body": body
        }

        self.logger.info(json.dumps(log_entry))

    def log_upstream_response(
        self,
        request_id: str,
        status_code: int,
        headers: Dict[str, str],
        body: Any = None,
        response_time_ms: Optional[int] = None
    ):
        """
        Registra una respuesta de GLPI (upstream response).

        Args:
            request_id: ID de la petición original
            status_code: Código de estado HTTP
            headers: Headers de la respuesta
            body: Body de la respuesta
            response_time_ms: Tiempo de respuesta en milisegundos
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
            "type": "output",
            "direction": "glpi_to_proxy",
            "status_code": status_code,
            "headers": self._mask_sensitive_headers(headers),
            "body": body,
            "response_time_ms": response_time_ms
        }

        self.logger.info(json.dumps(log_entry))


# Instancia global del logger
proxy_logger = ProxyLogger()