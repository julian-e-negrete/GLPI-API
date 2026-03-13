"""
GLPI API Proxy - Aplicación Principal.
Capa intermedia para centralizar la comunicación con la API de GLPI v2.2.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware.logging import LoggingMiddleware
from app.routes import token, health, proxy


# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Obtener configuración
settings = get_settings()

# Crear aplicación FastAPI
app = FastAPI(
    title="GLPI API Proxy",
    description="Capa intermedia para centralizar la comunicación con la API de GLPI v2.2",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Agregar middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agregar middleware de logging
app.add_middleware(LoggingMiddleware)

# Registrar rutas
app.include_router(token.router)
app.include_router(health.router)
app.include_router(proxy.router)


@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación."""
    logger.info("=" * 60)
    logger.info("GLPI API Proxy iniciando...")
    logger.info(f"Servidor GLPI: {settings.glpi_api_url}")
    logger.info(f"Puerto del proxy: {settings.proxy_port}")
    logger.info(f"Nivel de logging: {settings.log_level}")
    logger.info(f"Directorio de logs: {settings.log_dir}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Evento de cierre de la aplicación."""
    logger.info("GLPI API Proxy cerrando...")
    # Cerrar cliente HTTP
    from app.services.glpi_client import glpi_client
    await glpi_client.close()
    logger.info("GLPI API Proxy cerrado correctamente")


@app.get("/")
async def root():
    """Endpoint raíz con información del servicio."""
    return {
        "service": "GLPI API Proxy",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v2.2/Health",
        "glpi_server": settings.glpi_api_url
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.proxy_host,
        port=settings.proxy_port,
        reload=True,
        log_level=settings.log_level.lower()
    )