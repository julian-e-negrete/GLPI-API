"""
Modelos de datos para requests y responses.
"""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ProxyRequest(BaseModel):
    """Modelo genérico para requests al proxy."""
    method: str = Field(..., description="Método HTTP")
    path: str = Field(..., description="Path del endpoint")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Headers adicionales")
    body: Optional[Any] = Field(default=None, description="Cuerpo de la petición")
    query_params: Optional[Dict[str, str]] = Field(default=None, description="Query parameters")


class ProxyResponse(BaseModel):
    """Modelo genérico para responses del proxy."""
    status_code: int = Field(..., description="Código de estado HTTP")
    headers: Dict[str, str] = Field(default_factory=dict, description="Headers de respuesta")
    body: Any = Field(..., description="Cuerpo de la respuesta")


class HealthResponse(BaseModel):
    """Respuesta del endpoint de salud."""
    status: str = Field(..., description="Estado del servicio")
    service: str = Field(default="glpi-api-proxy", description="Nombre del servicio")
    version: str = Field(default="1.0.0", description="Versión del servicio")
    glpi_connected: bool = Field(..., description="Conexión con GLPI disponible")
    token_valid: Optional[bool] = Field(default=None, description="Token actual válido")


class LogEntry(BaseModel):
    """Entrada de log en formato JSON."""
    timestamp: str = Field(..., description="Timestamp ISO 8601")
    request_id: str = Field(..., description="ID único de request")
    type: str = Field(..., description="Tipo: input|output|error")
    direction: str = Field(..., description="Dirección del flujo")
    method: Optional[str] = Field(default=None, description="Método HTTP")
    path: Optional[str] = Field(default=None, description="Path del endpoint")
    headers: Dict[str, str] = Field(default_factory=dict, description="Headers")
    body: Optional[Any] = Field(default=None, description="Cuerpo")
    status_code: Optional[int] = Field(default=None, description="Código de estado")
    response_time_ms: Optional[int] = Field(default=None, description="Tiempo de respuesta")
    source_ip: Optional[str] = Field(default=None, description="IP origen")
    error: Optional[str] = Field(default=None, description="Mensaje de error")