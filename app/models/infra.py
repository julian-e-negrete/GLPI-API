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
    databases: list[dict] = []
    note: str = ""


class ComputerUpsertResponse(BaseModel):
    """Respuesta de la operación upsert sobre un Computer."""
    status: Literal["created", "updated", "error"]
    glpi_id: Optional[int] = None
    error: Optional[str] = None


class DbInstanceResult(BaseModel):
    """Resultado de la creación de una instancia de base de datos."""
    name: str
    id: Optional[int] = None
    status: Literal["created", "error"]


class NoteResult(BaseModel):
    """Resultado de la creación de una nota."""
    id: Optional[int] = None
    status: Literal["created", "error"]


class ServerRegistrationResponse(BaseModel):
    """Respuesta completa del registro de un servidor."""
    computer: ComputerUpsertResponse
    db_instances: list[DbInstanceResult]
    note: NoteResult


class SeedResponse(BaseModel):
    """Respuesta del endpoint de seed con el resumen de todos los servidores."""
    results: dict[str, ServerRegistrationResponse]


@dataclass
class UpsertResult:
    """Resultado interno del servicio para operaciones upsert."""
    status: Literal["created", "updated", "error"]
    glpi_id: Optional[int] = None
    error: Optional[str] = None


@dataclass
class ServerRegistrationResult:
    """Resultado interno del registro completo de un servidor."""
    computer: UpsertResult
    db_instances: list[dict] = field(default_factory=list)
    note: dict = field(default_factory=dict)
