"""
Servicio de gestión OAuth para GLPI API.
Maneja la autenticación y renovación de tokens de acceso.
"""
import httpx
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.config import get_settings
from app.models.token import TokenRequest, TokenResponse, TokenData, ErrorResponse


logger = logging.getLogger(__name__)


class OAuthManager:
    """Gestor de autenticación OAuth."""

    def __init__(self):
        self.settings = get_settings()
        self._token_data: Optional[TokenData] = None

    async def get_token(self, username: Optional[str] = None, password: Optional[str] = None, scope: str = "api user") -> TokenResponse:
        user = username or self.settings.glpi_username
        pwd = password or self.settings.glpi_password

        if not user or not pwd:
            raise ValueError("Credenciales de usuario requeridas")

        # Always send as form-urlencoded with explicit scope — GLPI ignores scope in JSON
        async with httpx.AsyncClient(timeout=self.settings.http_timeout) as client:
            response = await client.post(
                self.settings.token_url,
                data={
                    "grant_type": "password",
                    "client_id": self.settings.glpi_client_id,
                    "client_secret": self.settings.glpi_client_secret,
                    "username": user,
                    "password": pwd,
                    "scope": scope,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error_description", "Unknown error")
                except Exception:
                    error_msg = response.text

                logger.error(f"Error en autenticación OAuth: {error_msg}")
                raise httpx.HTTPStatusError(
                    error_msg,
                    request=response.request,
                    response=response
                )

            token_response = TokenResponse(**response.json())

            # Almacenar token con fecha de expiración
            self._token_data = TokenData(
                access_token=token_response.access_token,
                expires_at=datetime.utcnow() + timedelta(seconds=token_response.expires_in),
                token_type=token_response.token_type
            )

            logger.info(f"Token OAuth obtenido exitosamente, expira en {token_response.expires_in}s")
            return token_response

    def get_cached_token(self) -> Optional[str]:
        """
        Retorna el token actual si existe y no ha expirado.

        Returns:
            Token de acceso o None si no existe o expiró
        """
        if self._token_data is None:
            return None

        if self._token_data.is_expired:
            logger.info("Token expirado, no se retorna")
            self._token_data = None
            return None

        return self._token_data.access_token

    def is_token_valid(self) -> bool:
        """Verifica si hay un token válido en caché."""
        if self._token_data is None:
            return False

        return not self._token_data.is_expired

    def clear_token(self):
        """Limpia el token almacenado."""
        self._token_data = None
        logger.info("Token limpiado de la caché")

    async def ensure_valid_token(self) -> str:
        """
        Asegura que existe un token válido, obteniéndolo si es necesario.

        Returns:
            Token de acceso válido

        Raises:
            ValueError: Si no se pueden obtener credenciales
            httpx.HTTPStatusError: Si falla la autenticación
        """
        # Verificar si hay token válido en caché
        cached_token = self.get_cached_token()
        if cached_token:
            return cached_token

        # Obtener nuevo token
        return (await self.get_token()).access_token

    def get_bearer_token_header(self) -> dict:
        """
        Retorna el header Authorization con el Bearer token.

        Returns:
            Dict con el header Authorization
        """
        token = self.get_cached_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}


# Instancia global del gestor OAuth
oauth_manager = OAuthManager()