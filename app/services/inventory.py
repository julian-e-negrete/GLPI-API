"""
Servicio de inventario de infraestructura para GLPI.
Gestiona la creación y actualización de assets de tipo Computer,
DatabaseInstance y Note.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.models.infra import ServerRegistrationResult, TicketResponse, UpsertResult
from app.services.glpi_client import GLPIClient
from app.services.oauth import oauth_manager

logger = logging.getLogger(__name__)

COMPUTER_ENDPOINT = "/api.php/v2.2/Assets/Computer"
DB_INSTANCE_ENDPOINT = "/api.php/v2.2/Management/DatabaseInstance"


class InventoryService:
    """Servicio para gestionar el inventario de infraestructura en GLPI."""

    def __init__(self, client: GLPIClient):
        self.client = client

    async def _ensure_token(self) -> None:
        """Asegura que el oauth_manager tiene un token válido cacheado."""
        await oauth_manager.ensure_valid_token()

    async def _find_by_name(self, name: str) -> Optional[int]:
        """Busca un Computer por nombre exacto y retorna su id, o None si no existe.
        
        Nota: el parámetro searchText de GLPI no filtra correctamente, por lo que
        se obtiene la lista completa y se filtra en Python por nombre exacto.
        """
        try:
            response = await self.client.get(
                COMPUTER_ENDPOINT,
                params={"range": "0-500"},
            )
            if response.status_code != 200:
                return None
            items = response.json()
            if not items:
                return None
            for item in items:
                if item.get("name") == name and not item.get("is_deleted", False):
                    return item["id"]
            return None
        except Exception as e:
            logger.error(f"Error buscando Computer por nombre '{name}': {e}")
            return None

    async def upsert_computer(
        self,
        name: str,
        ip_local: str,
        role: str,
        note_content: str = "",
    ) -> UpsertResult:
        """Crea o actualiza un Computer en GLPI (upsert por nombre)."""
        try:
            await self._ensure_token()
            existing_id = await self._find_by_name(name)
            comment = f"Rol: {role} | IP: {ip_local}"
            if note_content:
                comment = f"{comment} | {note_content}"
            payload = {"name": name, "comment": comment}

            if existing_id is None:
                response = await self.client.post(COMPUTER_ENDPOINT, json_data=payload)
                if response.status_code in (200, 201):
                    return UpsertResult(status="created", glpi_id=response.json()["id"])
                return UpsertResult(
                    status="error",
                    error=f"{response.status_code}: {response.text}",
                )
            else:
                response = await self.client.patch(
                    f"{COMPUTER_ENDPOINT}/{existing_id}", json_data=payload
                )
                if response.status_code in (200, 201):
                    return UpsertResult(status="updated", glpi_id=existing_id)
                return UpsertResult(
                    status="error",
                    error=f"{response.status_code}: {response.text}",
                )
        except Exception as e:
            logger.error(f"Error en upsert_computer para '{name}': {e}")
            return UpsertResult(status="error", error=str(e))

    async def create_db_instances(
        self,
        computer_id: int,
        databases: list[dict],
    ) -> list[dict]:
        """Crea DatabaseInstance en GLPI vinculadas al Computer dado."""
        results = []
        for db in databases:
            try:
                payload = {
                    "name": db["name"],
                    "port": db.get("port"),
                    "version": db.get("version"),
                    "is_active": True,
                    "itemtype": "Computer",
                    "items_id": computer_id,
                    "comment": db.get("comment", ""),
                }
                response = await self.client.post(DB_INSTANCE_ENDPOINT, json_data=payload)
                if response.status_code in (200, 201):
                    results.append({"name": db["name"], "id": response.json()["id"], "status": "created"})
                else:
                    results.append({"name": db["name"], "id": None, "status": "error"})
            except Exception as e:
                logger.error(f"Error creando DatabaseInstance '{db.get('name')}': {e}")
                results.append({"name": db.get("name"), "id": None, "status": "error"})
        return results

    async def create_note(self, computer_id: int, content: str) -> dict:
        """Crea una Note asociada al Computer dado."""
        try:
            response = await self.client.post(
                f"{COMPUTER_ENDPOINT}/{computer_id}/Note",
                json_data={"content": content},
            )
            if response.status_code in (200, 201):
                return {"id": response.json()["id"], "status": "created"}
            return {"id": None, "status": "error"}
        except Exception as e:
            logger.error(f"Error creando Note para computer_id={computer_id}: {e}")
            return {"id": None, "status": "error"}

    async def register_server(
        self,
        name: str,
        ip_local: str,
        ip_tailscale: str,
        role: str,
        databases: list[dict],
        note_content: str,
    ) -> ServerRegistrationResult:
        """Orquesta el registro completo de un servidor: Computer + DBs + Note."""
        computer_result = await self.upsert_computer(name, ip_local, role, note_content)

        if computer_result.status == "error":
            return ServerRegistrationResult(
                computer=computer_result,
                db_instances=[],
                note={"id": None, "status": "error"},
            )

        db_results = await self.create_db_instances(computer_result.glpi_id, databases)
        # La nota se incorpora en el comment del Computer durante el upsert
        note_result = {"id": computer_result.glpi_id, "status": "created"}

        return ServerRegistrationResult(
            computer=computer_result,
            db_instances=db_results,
            note=note_result,
        )

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


TICKET_ENDPOINT = "/api.php/v2.2/Assistance/Ticket"

# Mapeo de status GLPI
TICKET_STATUS = {1: "Nuevo", 2: "En curso (asignado)", 3: "En curso (planificado)", 4: "Pendiente", 5: "Resuelto", 6: "Cerrado"}


class TicketService:
    """Servicio para gestionar tickets de GLPI vinculados a servidores."""

    def __init__(self, client: GLPIClient, inventory: InventoryService):
        self.client = client
        self.inventory = inventory

    async def _resolve_computer(self, server_name: str) -> Optional[int]:
        """Retorna el computer_id de un servidor por nombre, o None si no existe."""
        return await self.inventory._find_by_name(server_name)

    def _parse_ticket(self, t: dict, computer_id: Optional[int] = None, computer_name: Optional[str] = None) -> TicketResponse:
        status = t.get("status", {})
        status_id = status.get("id", 0) if isinstance(status, dict) else status
        status_name = status.get("name", "") if isinstance(status, dict) else TICKET_STATUS.get(status_id, "")
        # Extraer agente del campo content si fue embebido
        content = t.get("content", "")
        agent = None
        if content.startswith("[agent:") and "]" in content:
            agent = content[7:content.index("]")]
            content = content[content.index("]") + 1:].strip()
        return TicketResponse(
            id=t["id"],
            title=t["name"],
            description=content,
            status_id=status_id,
            status_name=status_name,
            computer_id=computer_id,
            computer_name=computer_name,
            agent=agent,
        )

    async def create_ticket(self, server_name: str, title: str, description: str, agent: str, urgency: int) -> dict:
        """Crea un ticket en GLPI vinculado al Computer del servidor dado."""
        await self.inventory._ensure_token()
        computer_id = await self._resolve_computer(server_name)
        if computer_id is None:
            return {"error": f"Servidor '{server_name}' no encontrado en GLPI"}

        # Embebemos el agente en el content para trazabilidad
        content = f"[agent:{agent}] {description}"
        payload = {
            "name": title,
            "content": content,
            "urgency": urgency,
            "type": 2,  # demanda (no incidente)
            "items_id": computer_id,
            "itemtype": "Computer",
        }
        response = await self.client.post(TICKET_ENDPOINT, json_data=payload)
        if response.status_code not in (200, 201):
            return {"error": f"{response.status_code}: {response.text}"}
        ticket_id = response.json()["id"]
        return {"id": ticket_id, "status": "created", "computer_id": computer_id}

    async def list_tickets(self, server_name: str) -> list[TicketResponse]:
        """Lista todos los tickets activos vinculados a un servidor."""
        await self.inventory._ensure_token()
        computer_id = await self._resolve_computer(server_name)
        if computer_id is None:
            return []

        response = await self.client.get(TICKET_ENDPOINT, params={"range": "0-500"})
        if response.status_code != 200:
            return []

        tickets = response.json()
        result = []
        for t in tickets:
            if t.get("is_deleted"):
                continue
            result.append(self._parse_ticket(t, computer_id, server_name))
        return result

    async def complete_ticket(self, ticket_id: int, solution: str) -> dict:
        """Marca un ticket como resuelto (status=5) con una solución."""
        await self.inventory._ensure_token()
        payload = {"status": 5, "solution": solution}
        response = await self.client.patch(f"{TICKET_ENDPOINT}/{ticket_id}", json_data=payload)
        if response.status_code not in (200, 201):
            return {"error": f"{response.status_code}: {response.text}"}
        return {"id": ticket_id, "status": "resolved"}
