"""
Modelos de datos para el inventario de infraestructura GLPI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from pydantic import BaseModel


class ComputerUpsertRequest(BaseModel):
    """Request para crear o actualizar un asset Computer en GLPI."""
    name: str
    ip_local: str
    ip_tailscale: str
    role: str
    services: list[str] = []
    detail: Optional[str] = None


class ComputerUpsertResponse(BaseModel):
    """Respuesta de la operación upsert sobre un Computer."""
    status: Literal["created", "updated", "error"]
    glpi_id: Optional[int] = None
    error: Optional[str] = None


class SeedResponse(BaseModel):
    """Respuesta del endpoint de seed con el resumen de todos los servidores."""
    results: dict[str, ComputerUpsertResponse]


@dataclass
class UpsertResult:
    """Resultado interno del servicio para operaciones upsert."""
    status: Literal["created", "updated", "error"]
    glpi_id: Optional[int] = None
    error: Optional[str] = None
