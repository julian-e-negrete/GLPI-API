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
            "PostgreSQL-marketdata",
            "MySQL-investments",
            "Binance-API",
            "Matriz-scraping",
            "SMTP-alerts",
            "GLPI-API-Proxy",
        ],
        "detail": (
            "=== PostgreSQL (marketdata) ===\n"
            "PG_HOST=localhost | PG_PORT=5432 | PG_DBNAME=marketdata | PG_USER=postgres\n\n"
            "=== MySQL (investments) ===\n"
            "MYSQL_HOST=localhost | MYSQL_USER=black | MYSQL_DATABASE=investments\n\n"
            "=== Matriz Web Scraping ===\n"
            "MATRIZ_USER=20452373484\n\n"
            "=== Binance API ===\n"
            "BINANCE_API_KEY=60H2cfydHlhKryRGJbCwWbqbX7lNMAVQjRmier9gy5mx8o0HnlRkRVkKNR7DG9Vr\n\n"
            "=== SMTP Alerts ===\n"
            "SMTP_SERVER=smtp.gmail.com | SMTP_PORT=587\n"
            "EMAIL_SENDER=[email_sender] | EMAIL_RECEIVER=[email_receiver]\n\n"
            "=== GLPI API Proxy ===\n"
            "GLPI_API_URL=http://192.168.1.33:80 | PROXY_HOST=0.0.0.0 | PROXY_PORT=8080\n"
            "GLPI_USERNAME=HaraiDasan"
        ),
    },
    {
        "name": "SRV-GLPI-PROCESSOR",
        "ip_local": "192.168.1.33",
        "ip_tailscale": "100.70.84.114",
        "role": "glpi-processor",
        "services": [
            "GLPI",
            "MySQL-investments",
            "PostgreSQL-marketdata",
            "HFT-SDK",
            "PPI-API",
            "Binance",
        ],
        "detail": (
            "=== GLPI ===\n"
            "URL=http://192.168.1.33:80\n\n"
            "=== MySQL (investments) ===\n"
            "DB_HOST=100.112.16.115 | DB_PORT=3306 | DB_USER=haraidasan | DB_NAME=investments\n\n"
            "=== PostgreSQL (marketdata) ===\n"
            "POSTGRES_HOST=100.112.16.115 | POSTGRES_PORT=5432 | POSTGRES_USER=postgres | POSTGRES_DB=marketdata\n\n"
            "=== HFT Database (PostgreSQL - Market Data) ===\n"
            "HFT_DB_HOST=100.112.16.115 | HFT_DB_PORT=5432 | HFT_DB_DB=marketdata\n\n"
            "=== Matriz Web Scraping ===\n"
            "MATRIZ_USER=20452373484\n\n"
            "=== HFT SDK ===\n"
            "HFT_SDK_API_KEY_PROD=[prod_key] | HFT_SDK_API_KEY_UAT=[uat_key]\n\n"
            "=== PPI (Portfolio Personal Inversiones) ===\n"
            "PPI_PUBLIC_KEY=[public_key] | PPI_PRIVATE_KEY=[private_key]\n\n"
            "=== Binance ===\n"
            "BINANCE_API_KEY=60H2cfydHlhKryRGJbCwWbqbX7lNMAVQjRmier9gy5mx8o0HnlRkRVkKNR7DG9Vr"
        ),
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
        detail=body.detail,
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
                detail=server.get("detail"),
            )
            results[server["name"]] = ComputerUpsertResponse(
                status=result.status,
                glpi_id=result.glpi_id,
                error=result.error,
            )
        except Exception as e:
            results[server["name"]] = ComputerUpsertResponse(status="error", error=str(e))

    return SeedResponse(results=results)
