"""
Rutas de salud y estado del proxy.
"""
from fastapi import APIRouter

from app.models.requests import HealthResponse
from app.services.glpi_client import glpi_client
from app.services.oauth import oauth_manager


router = APIRouter(prefix="/api/v2.2", tags=["Health"])


@router.get("/Health", response_model=HealthResponse)
async def health_check():
    """
    Verifica el estado del proxy y la conexión con GLPI.

    Returns:
        HealthResponse con el estado del servicio
    """
    # Verificar conexión con GLPI
    glpi_connected = await glpi_client.check_connection()

    # Verificar token
    token_valid = None
    if oauth_manager.is_token_valid():
        token_valid = True

    status = "healthy" if glpi_connected else "degraded"

    return HealthResponse(
        status=status,
        service="glpi-api-proxy",
        version="1.0.0",
        glpi_connected=glpi_connected,
        token_valid=token_valid
    )


@router.get("/ping")
async def ping():
    """
    Endpoint simple de ping para verificación rápida.

    Returns:
        Mensaje de respuesta
    """
    return {
        "service": "glpi-api-proxy",
        "status": "ok",
        "version": "1.0.0"
    }