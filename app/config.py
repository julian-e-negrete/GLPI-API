"""
Configuración de la aplicación GLPI API Proxy.
Carga variables de entorno y provee acceso centralizado a la configuración.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Configuración de la aplicación."""

    # Configuración del modelo Pydantic
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Configuración del servidor GLPI
    glpi_api_url: str = Field(
        default="http://192.168.1.33:80",
        description="URL base del servidor GLPI"
    )

    # Credenciales OAuth
    glpi_client_id: str = Field(
        default="",
        description="ID de cliente OAuth"
    )
    glpi_client_secret: str = Field(
        default="",
        description="Secreto del cliente OAuth"
    )

    # Credenciales de usuario
    glpi_username: str = Field(
        default="",
        description="Usuario GLPI"
    )
    glpi_password: str = Field(
        default="",
        description="Password del usuario GLPI"
    )

    # Configuración del Proxy
    proxy_host: str = Field(
        default="0.0.0.0",
        description="Host donde correrá el proxy"
    )
    proxy_port: int = Field(
        default=8080,
        description="Puerto donde correrá el proxy"
    )

    # Configuración de Logging
    log_level: str = Field(
        default="INFO",
        description="Nivel de logging"
    )
    log_dir: str = Field(
        default="./logs",
        description="Directorio donde se almacenarán los logs"
    )

    # Configuración HTTP
    http_timeout: int = Field(
        default=30,
        description="Timeout para requests HTTP en segundos"
    )

    @property
    def token_url(self) -> str:
        """Retorna la URL completa para obtener el token."""
        return f"{self.glpi_api_url}/api.php/v2.2/token"

    @property
    def glpi_headers_default(self) -> dict:
        """Headers obligatorios para todas las peticiones a GLPI."""
        return {
            "Accept": "application/json",
            "GLPI-Entity-Recursive": "true",
            "Accept-Language": "en_GB"
        }

    def ensure_log_dir(self) -> Path:
        """Crea el directorio de logs si no existe."""
        log_path = Path(self.log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        return log_path


# Instancia global de configuración
settings = Settings()


def get_settings() -> Settings:
    """Retorna la instancia de configuración."""
    return settings