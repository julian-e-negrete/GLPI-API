"""
Router de infraestructura para gestionar el inventario de Computers en GLPI.
"""
from fastapi import APIRouter, HTTPException

from app.models.infra import ComputerUpsertRequest, ComputerUpsertResponse, SeedResponse
from app.services.inventory import InventoryService
from app.services.glpi_client import glpi_client


router = APIRouter(prefix="/api/v2.2/infra", tags=["Infraestructura"])

SEED_SERVERS = [
    {
        "name": "SRV-SCRAPING-PROXY",
        "ip_local": "192.168.1.244",
        "ip_tailscale": "100.112.16.115",
        "role": "scraping-proxy",
        "services": [
            "PostgreSQL-marketdata", "MySQL-investments", "Binance-API",
            "Matriz-scraping", "SMTP-alerts", "GLPI-API-Proxy",
        ],
    },
    {
        "name": "SRV-GLPI-PROCESSOR",
        "ip_local": "192.168.1.33",
        "ip_tailscale": "100.70.84.114",
        "role": "glpi-processor",
        "services": [
            "GLPI", "MySQL-investments", "PostgreSQL-marketdata",
            "HFT-SDK", "PPI-API", "Binance",
        ],
    },
]


@router.post("/computers", response_model=ComputerUpsertResponse)
async def upsert_computer(body: ComputerUpsertRequest):
    """Crea o actualiza un Computer en GLPI."""
    service = InventoryService(glpi_client)
    result = await service.upsert_computer(
        name=body.name,
        ip_local=body.ip_local,
        ip_tailscale=body.ip_tailscale,
        role=body.role,
        services=body.services,
    )
    if result.status == "error":
        raise HTTPException(status_code=502, detail=result.error)
    return ComputerUpsertResponse(status=result.status, glpi_id=result.glpi_id)


@router.get("/computers")
async def list_computers():
    """Retorna la lista de todos los Computers registrados en GLPI."""
    service = InventoryService(glpi_client)
    return await service.list_computers()


@router.post("/seed", response_model=SeedResponse)
async def seed_servers():
    """Ejecuta el seed de servidores conocidos en GLPI."""
    service = InventoryService(glpi_client)
    results: dict[str, ComputerUpsertResponse] = {}

    for server in SEED_SERVERS:
        try:
            result = await service.upsert_computer(
                name=server["name"],
                ip_local=server["ip_local"],
                ip_tailscale=server["ip_tailscale"],
                role=server["role"],
                services=server["services"],
            )
            results[server["name"]] = ComputerUpsertResponse(
                status=result.status,
                glpi_id=result.glpi_id,
                error=result.error,
            )
        except Exception as e:
            results[server["name"]] = ComputerUpsertResponse(status="error", error=str(e))

    return SeedResponse(results=results)
