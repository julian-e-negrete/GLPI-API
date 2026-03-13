"""
Cliente HTTP para comunicarse con la API de GLPI.
Maneja todas las peticiones hacia el servidor GLPI.
"""
import httpx
from typing import Any, Dict, Optional
import logging

from app.config import get_settings
from app.services.oauth import oauth_manager


logger = logging.getLogger(__name__)


class GLPIClient:
    """Cliente para interactuar con la API de GLPI."""

    def __init__(self):
        self.settings = get_settings()
        self.oauth = oauth_manager
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Obtiene o crea el cliente HTTP."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.http_timeout),
                follow_redirects=True
            )
        return self._client

    async def close(self):
        """Cierra el cliente HTTP."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _build_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Construye los headers para la petición a GLPI.

        Args:
            additional_headers: Headers adicionales a incluir

        Returns:
            Dict con todos los headers
        """
        # Headers obligatorios
        headers = self.settings.glpi_headers_default.copy()

        # Agregar Bearer token si existe
        bearer_header = self.oauth.get_bearer_token_header()
        headers.update(bearer_header)

        # Agregar headers adicionales
        if additional_headers:
            headers.update(additional_headers)

        return headers

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """
        Realiza una petición a la API de GLPI.

        Args:
            method: Método HTTP (GET, POST, PUT, DELETE, PATCH)
            endpoint: Endpoint de la API (ej: /api.php/v2.2/Administration/User)
            params: Query parameters
            json_data: Body en formato JSON
            data: Body en formato form-urlencoded
            headers: Headers adicionales

        Returns:
            Response de httpx

        Raises:
            httpx.HTTPStatusError: Si la petición falla
        """
        # Construir URL completa
        url = f"{self.settings.glpi_api_url}{endpoint}"

        # Construir headers
        request_headers = self._build_headers(headers)

        # Loggear la petición
        logger.info(f"Petición a GLPI: {method} {url}")

        # Realizar petición
        client = await self._get_client()
        response = await client.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            data=data,
            headers=request_headers
        )

        # Loggear respuesta
        logger.info(f"Respuesta de GLPI: {response.status_code}")

        return response

    # Métodos de conveniencia
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """Realiza una petición GET."""
        return await self.request("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None
    ) -> httpx.Response:
        """Realiza una petición POST."""
        return await self.request("POST", endpoint, json_data=json_data, data=data)

    async def put(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        """Realiza una petición PUT."""
        return await self.request("PUT", endpoint, json_data=json_data)

    async def delete(self, endpoint: str) -> httpx.Response:
        """Realiza una petición DELETE."""
        return await self.request("DELETE", endpoint)

    async def patch(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        """Realiza una petición PATCH."""
        return await self.request("PATCH", endpoint, json_data=json_data)

    async def check_connection(self) -> bool:
        """
        Verifica la conexión con el servidor GLPI.

        Returns:
            True si hay conexión, False si no
        """
        try:
            response = await self.get("/api.php/v2.2/init")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error al verificar conexión con GLPI: {e}")
            return False


# Instancia global del cliente GLPI
glpi_client = GLPIClient()