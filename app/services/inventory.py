"""
Servicio de inventario de infraestructura para GLPI.
Gestiona la creación y actualización de assets de tipo Computer.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.models.infra import UpsertResult
from app.services.glpi_client import GLPIClient
from app.services.oauth import oauth_manager

logger = logging.getLogger(__name__)

COMPUTER_ENDPOINT = "/api.php/v2.2/Assets/Computer"


class InventoryService:
    """Servicio para gestionar el inventario de Computers en GLPI."""

    def __init__(self, client: GLPIClient):
        self.client = client

    # ------------------------------------------------------------------
    # Sub-tarea 2.1
    # ------------------------------------------------------------------
    def _build_comment(
        self,
        ip_local: str,
        ip_tailscale: str,
        role: str,
        services: list[str],
    ) -> str:
        """Construye el campo comment con el formato estándar."""
        svc_str = ", ".join(services) if services else "—"
        return (
            f"Servicios: {svc_str} | "
            f"IP: {ip_local} | "
            f"Tailscale: {ip_tailscale} | "
            f"Rol: {role}"
        )

    # ------------------------------------------------------------------
    # Sub-tarea 2.3
    # ------------------------------------------------------------------
    async def _ensure_token(self) -> None:
        """Asegura que el oauth_manager tiene un token válido cacheado."""
        await oauth_manager.ensure_valid_token()

    async def _find_by_name(self, name: str) -> Optional[int]:
        """Busca un Computer por nombre exacto y retorna su id, o None si no existe."""
        try:
            response = await self.client.get(
                COMPUTER_ENDPOINT,
                params={"searchText[name]": name, "range": "0-100"},
            )
            if response.status_code != 200:
                return None
            items = response.json()
            if not items:
                return None
            # Filtrar por nombre exacto (GLPI hace búsqueda parcial)
            for item in items:
                if item.get("name") == name and not item.get("is_deleted", False):
                    return item["id"]
            return None
        except Exception as e:
            logger.error(f"Error buscando Computer por nombre '{name}': {e}")
            return None

    # ------------------------------------------------------------------
    # Sub-tarea 2.4
    # ------------------------------------------------------------------
    async def upsert_computer(
        self,
        name: str,
        ip_local: str,
        ip_tailscale: str,
        role: str,
        services: list[str],
    ) -> UpsertResult:
        """Crea o actualiza un Computer en GLPI (upsert por nombre)."""
        try:
            await self._ensure_token()
            existing_id = await self._find_by_name(name)
            comment = self._build_comment(ip_local, ip_tailscale, role, services)
            payload = {"name": name, "comment": comment}

            if existing_id is None:
                # Crear nuevo asset
                response = await self.client.post(COMPUTER_ENDPOINT, json_data=payload)
                if response.status_code == 201:
                    return UpsertResult(status="created", glpi_id=response.json()["id"])
                return UpsertResult(
                    status="error",
                    error=f"{response.status_code}: {response.text}",
                )
            else:
                # Actualizar asset existente
                response = await self.client.patch(
                    f"{COMPUTER_ENDPOINT}/{existing_id}", json_data=payload
                )
                if response.status_code == 200:
                    return UpsertResult(status="updated", glpi_id=existing_id)
                return UpsertResult(
                    status="error",
                    error=f"{response.status_code}: {response.text}",
                )
        except Exception as e:
            logger.error(f"Error en upsert_computer para '{name}': {e}")
            return UpsertResult(status="error", error=str(e))

    # ------------------------------------------------------------------
    # Sub-tarea 2.8
    # ------------------------------------------------------------------
    async def list_computers(self) -> list[dict]:
        """Retorna la lista de todos los Computers registrados en GLPI."""
        try:
            response = await self.client.get(COMPUTER_ENDPOINT)
            if response.status_code != 200:
                return []
            return response.json()
        except Exception as e:
            logger.error(f"Error listando Computers: {e}")
            return []
