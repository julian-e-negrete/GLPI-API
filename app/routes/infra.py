"""
Router de infraestructura para gestionar el inventario de Computers en GLPI.
"""
from fastapi import APIRouter

from app.models.infra import (
    ComputerUpsertRequest,
    ComputerUpsertResponse,
    DbInstanceResult,
    NoteResult,
    SeedResponse,
    ServerRegistrationResponse,
    TicketCompleteRequest,
    TicketCreateRequest,
    TicketResponse,
)
from app.services.glpi_client import glpi_client
from app.services.inventory import InventoryService, TicketService

router = APIRouter(prefix="/api/v2.2/infra", tags=["Infraestructura"])

SEED_SERVERS = [
    {
        "name": "SRV-SCRAPING-PROXY",
        "ip_local": "192.168.1.244",
        "ip_tailscale": "100.112.16.115",
        "role": "scraping-proxy",
        "databases": [
            {"name": "marketdata-pg", "port": 5432, "version": "PostgreSQL", "comment": "PG_HOST=localhost | PG_USER=postgres | PG_DBNAME=marketdata"},
            {"name": "investments-mysql", "port": 3306, "version": "MySQL", "comment": "MYSQL_HOST=localhost | MYSQL_USER=black | MYSQL_DATABASE=investments"},
        ],
        "note": "Tailscale: 100.112.16.115 | Binance API: key=60H2cfydHlhKryRGJbCwWbqbX7lNMAVQjRmier9gy5mx8o0HnlRkRVkKNR7DG9Vr | Matriz scraping: user=20452373484 | SMTP: smtp.gmail.com:587 sender=juliannegrete77@gmail.com | GLPI Proxy: port=8080",
    },
    {
        "name": "SRV-GLPI-PROCESSOR",
        "ip_local": "192.168.1.33",
        "ip_tailscale": "100.70.84.114",
        "role": "glpi-processor",
        "databases": [
            {"name": "investments-mysql-proc", "port": 3306, "version": "MySQL", "comment": "DB_HOST=100.112.16.115 | DB_USER=haraidasan | DB_NAME=investments"},
            {"name": "marketdata-pg-proc", "port": 5432, "version": "PostgreSQL", "comment": "POSTGRES_HOST=100.112.16.115 | POSTGRES_USER=postgres | POSTGRES_DB=marketdata"},
            {"name": "marketdata-hft", "port": 5432, "version": "PostgreSQL", "comment": "HFT_DB_HOST=100.112.16.115 | HFT_DB_USER=postgres | HFT_DB_DB=marketdata"},
        ],
        "note": "Tailscale: 100.70.84.114 | GLPI: http://192.168.1.33:80 | HFT SDK: API_KEY_PROD=nuDX73vj2483KSUgvenkj9t50oA0vgvA4WcuRAER API_KEY_UAT=1ypnPqtlG64lJIjrRN0DNut0hlIcQ502MiAbyo2g | PPI API: PUBLIC_KEY=UG5kSHRnVlF5dVdQT2JQUGtRVlM= | Binance API: key=60H2cfydHlhKryRGJbCwWbqbX7lNMAVQjRmier9gy5mx8o0HnlRkRVkKNR7DG9Vr | Matriz: user=20452373484",
    },
]


def _to_server_registration_response(result) -> ServerRegistrationResponse:
    """Convierte un ServerRegistrationResult interno a ServerRegistrationResponse."""
    return ServerRegistrationResponse(
        computer=ComputerUpsertResponse(
            status=result.computer.status,
            glpi_id=result.computer.glpi_id,
            error=result.computer.error,
        ),
        db_instances=[
            DbInstanceResult(name=db["name"], id=db.get("id"), status=db["status"])
            for db in result.db_instances
        ],
        note=NoteResult(id=result.note.get("id"), status=result.note.get("status", "error")),
    )


@router.post("/computers", response_model=ServerRegistrationResponse)
async def register_computer(body: ComputerUpsertRequest):
    """Registra un servidor completo: Computer + DatabaseInstances + Note."""
    service = InventoryService(glpi_client)
    result = await service.register_server(
        name=body.name,
        ip_local=body.ip_local,
        ip_tailscale=body.ip_tailscale,
        role=body.role,
        databases=body.databases,
        note_content=body.note,
    )
    return _to_server_registration_response(result)


@router.get("/computers")
async def list_computers():
    """Retorna la lista de todos los Computers registrados en GLPI."""
    service = InventoryService(glpi_client)
    return await service.list_computers()


@router.post("/seed", response_model=SeedResponse)
async def seed_servers():
    """Ejecuta el seed de servidores conocidos en GLPI."""
    service = InventoryService(glpi_client)
    results: dict[str, ServerRegistrationResponse] = {}

    for server in SEED_SERVERS:
        try:
            result = await service.register_server(
                name=server["name"],
                ip_local=server["ip_local"],
                ip_tailscale=server["ip_tailscale"],
                role=server["role"],
                databases=server["databases"],
                note_content=server["note"],
            )
            results[server["name"]] = _to_server_registration_response(result)
        except Exception as e:
            results[server["name"]] = ServerRegistrationResponse(
                computer=ComputerUpsertResponse(status="error", error=str(e)),
                db_instances=[],
                note=NoteResult(status="error"),
            )

    return SeedResponse(results=results)


# --- Endpoints de Tickets por Servidor ---


def _get_ticket_service() -> TicketService:
    return TicketService(glpi_client, InventoryService(glpi_client))


@router.post("/servers/{server_name}/tickets")
async def create_server_ticket(server_name: str, body: TicketCreateRequest):
    """Crea un ticket en GLPI vinculado al servidor indicado."""
    svc = _get_ticket_service()
    return await svc.create_ticket(
        server_name=server_name,
        title=body.title,
        description=body.description,
        agent=body.agent,
        urgency=body.urgency,
        requester=body.requester,
    )


@router.get("/servers/{server_name}/tickets", response_model=list[TicketResponse])
async def list_server_tickets(server_name: str):
    """Lista todos los tickets activos del servidor indicado."""
    svc = _get_ticket_service()
    return await svc.list_tickets(server_name)


@router.patch("/servers/{server_name}/tickets/{ticket_id}/complete")
async def complete_server_ticket(server_name: str, ticket_id: int, body: TicketCompleteRequest):
    """Marca un ticket como resuelto."""
    svc = _get_ticket_service()
    return await svc.complete_ticket(ticket_id, body.solution)
