"""
Modelos de datos relacionados con OAuth y tokens.
"""
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    """Request para obtener token OAuth (Password Grant)."""
    grant_type: str = Field(default="password", description="Tipo de grant OAuth")
    client_id: str = Field(..., description="ID de cliente OAuth")
    client_secret: str = Field(..., description="Secreto del cliente")
    username: str = Field(..., description="Usuario GLPI")
    password: str = Field(..., description="Password del usuario")
    scope: Optional[str] = Field(default="api user", description="Scopes OAuth separados por espacio")


class TokenResponse(BaseModel):
    """Respuesta de token OAuth."""
    access_token: str = Field(..., description="Token de acceso")
    expires_in: int = Field(..., description="Segundos hasta expiración")
    token_type: str = Field(default="Bearer", description="Tipo de token")
    scope: Optional[str] = Field(default=None, description="Alcance del token")


class TokenData(BaseModel):
    """Datos del token almacenados en memoria."""
    access_token: str
    expires_at: datetime
    token_type: str = "Bearer"

    @property
    def is_expired(self) -> bool:
        """Verifica si el token ha expirado."""
        return datetime.utcnow() >= self.expires_at

    @property
    def is_expiring_soon(self, margin_seconds: int = 300) -> bool:
        """Verifica si el token expira pronto (5 minutos por defecto)."""
        return datetime.utcnow() >= (self.expires_at - timedelta(seconds=margin_seconds))


class ErrorResponse(BaseModel):
    """Respuesta de error estándar."""
    error: str = Field(..., description="Código de error")
    error_description: str = Field(..., description="Descripción del error")