"""
Tests unitarios para el GLPI API Proxy.
Valida conectividad, flujo de autenticación y logging.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json
import os
import sys

# Agregar el directorio app al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_settings():
    """Fixture para settings mockeados."""
    with patch('app.config.get_settings') as mock:
        settings = Mock()
        settings.glpi_api_url = "http://192.168.1.33:80"
        settings.token_url = "http://192.168.1.33:80/api.php/v2.2/token"
        settings.glpi_client_id = "test_client_id"
        settings.glpi_client_secret = "test_client_secret"
        settings.glpi_username = "test_user"
        settings.glpi_password = "test_password"
        settings.http_timeout = 30
        settings.log_level = "INFO"
        settings.log_dir = "./logs"
        settings.proxy_host = "0.0.0.0"
        settings.proxy_port = 8080
        settings.glpi_headers_default = {
            "Accept": "application/json",
            "GLPI-Entity-Recursive": "true",
            "Accept-Language": "en_GB"
        }
        settings.ensure_log_dir = Mock(return_value=MagicMock())
        mock.return_value = settings
        yield settings


@pytest.fixture
def mock_oauth_manager():
    """Fixture para OAuth manager mockeado."""
    with patch('app.services.oauth.oauth_manager') as mock:
        mock.get_token = AsyncMock()
        mock.get_cached_token = Mock(return_value=None)
        mock.is_token_valid = Mock(return_value=False)
        mock.clear_token = Mock()
        mock.get_bearer_token_header = Mock(return_value={})
        yield mock


# ============================================================================
# TESTS - CONFIGURACIÓN (TC-01)
# ============================================================================

class TestConfiguration:
    """Tests para la configuración del proxy."""

    def test_settings_loads_from_env(self, mock_settings):
        """TC-01: Verifica que la configuración se carga correctamente."""
        from app.config import Settings

        settings = Settings()
        assert settings.glpi_api_url == "http://192.168.1.33:80"
        assert settings.proxy_port == 8080

    def test_token_url_constructed(self, mock_settings):
        """TC-01: Verifica construcción de URL de token."""
        from app.config import Settings

        settings = Settings()
        assert settings.token_url == "http://192.168.1.33:80/api.php/v2.2/token"

    def test_glpi_headers_default(self, mock_settings):
        """TC-01: Verifica headers obligatorios."""
        from app.config import Settings

        settings = Settings()
        headers = settings.glpi_headers_default

        assert headers["Accept"] == "application/json"
        assert headers["GLPI-Entity-Recursive"] == "true"
        assert headers["Accept-Language"] == "en_GB"


# ============================================================================
# TESTS - AUTENTICACIÓN OAUTH (TC-04, TC-05, TC-06, TC-07)
# ============================================================================

class TestOAuth:
    """Tests para el flujo de autenticación OAuth."""

    @pytest.mark.asyncio
    async def test_get_token_success(self, mock_settings):
        """TC-04: Obtener token con credenciales válidas."""
        from app.services.oauth import OAuthManager

        manager = OAuthManager()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token_12345",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        mock_response.request = Mock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await manager.get_token()

            assert result.access_token == "test_token_12345"
            assert result.expires_in == 3600
            assert result.token_type == "Bearer"

    @pytest.mark.asyncio
    async def test_get_token_invalid_grant_type(self, mock_settings):
        """TC-05: Obtener token con grant_type inválido."""
        from app.services.oauth import OAuthManager

        manager = OAuthManager()

        with pytest.raises(ValueError, match="Credenciales de usuario requeridas"):
            await manager.get_token(username="", password="")

    @pytest.mark.asyncio
    async def test_get_token_invalid_credentials(self, mock_settings):
        """TC-06: Obtener token con credenciales inválidas."""
        from app.services.oauth import OAuthManager
        import httpx

        manager = OAuthManager()

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Invalid credentials"
        }
        mock_response.request = Mock()
        mock_response.text = "Unauthorized"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(httpx.HTTPStatusError):
                await manager.get_token(username="invalid", password="invalid")

    def test_token_caching(self, mock_settings):
        """TC-07: Verifica que el token se almacena en caché."""
        from app.services.oauth import OAuthManager

        manager = OAuthManager()

        # Verificar que no hay token inicialmente
        assert manager.get_cached_token() is None
        assert not manager.is_token_valid()

        # Simular token almacenado
        from app.models.token import TokenData
        manager._token_data = TokenData(
            access_token="cached_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            token_type="Bearer"
        )

        # Verificar que ahora hay token válido
        assert manager.get_cached_token() == "cached_token"
        assert manager.is_token_valid()

    def test_token_expiration(self, mock_settings):
        """TC-07: Verifica detección de token expirado."""
        from app.services.oauth import OAuthManager
        from app.models.token import TokenData

        manager = OAuthManager()

        # Token expirado
        manager._token_data = TokenData(
            access_token="expired_token",
            expires_at=datetime.utcnow() - timedelta(hours=1),
            token_type="Bearer"
        )

        assert manager._token_data.is_expired
        assert manager.get_cached_token() is None
        assert not manager.is_token_valid()


# ============================================================================
# TESTS - LOGGING (TC-08, TC-09, TC-10, TC-11, TC-12, TC-13, TC-14)
# ============================================================================

class TestLogging:
    """Tests para el sistema de logging."""

    def test_log_request_structure(self, mock_settings):
        """TC-08: Verifica estructura del log de request."""
        from app.services.logger import ProxyLogger

        with patch('app.services.logger.get_settings', return_value=mock_settings):
            with patch('app.services.logger.TimedRotatingFileHandler'):
                with patch('app.services.logger.jsonlogger.JsonFormatter'):
                    logger = ProxyLogger()

                    # Mock del logger
                    logger.logger = Mock()
                    logger.logger.info = Mock()

                    # Llamar log_request
                    logger.log_request(
                        method="POST",
                        path="/api/v2.2/Administration/User",
                        headers={"Content-Type": "application/json"},
                        body={"name": "test"},
                        direction="client_to_proxy",
                        source_ip="192.168.1.100"
                    )

                    # Verificar que se llamó al logger
                    assert logger.logger.info.called

    def test_log_response_structure(self, mock_settings):
        """TC-09: Verifica estructura del log de response."""
        from app.services.logger import ProxyLogger

        with patch('app.services.logger.get_settings', return_value=mock_settings):
            with patch('app.services.logger.TimedRotatingFileHandler'):
                with patch('app.services.logger.jsonlogger.JsonFormatter'):
                    logger = ProxyLogger()
                    logger.logger = Mock()
                    logger.logger.info = Mock()

                    logger.log_response(
                        request_id="test-uuid",
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=[{"id": 1}],
                        response_time_ms=150,
                        direction="proxy_to_client"
                    )

                    assert logger.logger.info.called

    def test_upstream_logging(self, mock_settings):
        """TC-10, TC-11: Verifica logging upstream."""
        from app.services.logger import ProxyLogger

        with patch('app.services.logger.get_settings', return_value=mock_settings):
            with patch('app.services.logger.TimedRotatingFileHandler'):
                with patch('app.services.logger.jsonlogger.JsonFormatter'):
                    logger = ProxyLogger()
                    logger.logger = Mock()
                    logger.logger.info = Mock()

                    # Request a GLPI
                    logger.log_upstream_request(
                        request_id="test-uuid",
                        method="GET",
                        url="http://192.168.1.33:80/api.php/v2.2/User",
                        headers={"Authorization": "Bearer token123"}
                    )

                    # Response de GLPI
                    logger.log_upstream_response(
                        request_id="test-uuid",
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body='[{"id": 1}]',
                        response_time_ms=100
                    )

                    assert logger.logger.info.call_count == 2

    def test_headers_in_log(self, mock_settings):
        """TC-12: Verifica que headers se incluyen en log."""
        from app.services.logger import ProxyLogger

        with patch('app.services.logger.get_settings', return_value=mock_settings):
            with patch('app.services.logger.TimedRotatingFileHandler'):
                with patch('app.services.logger.jsonlogger.JsonFormatter'):
                    logger = ProxyLogger()

                    test_headers = {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer test_token",
                        "X-Custom-Header": "value"
                    }

                    masked = logger._mask_sensitive_headers(test_headers)

                    assert masked["Content-Type"] == "application/json"
                    assert masked["X-Custom-Header"] == "value"

    def test_sensitive_data_masking(self, mock_settings):
        """TC-14: Verifica enmascaramiento de datos sensibles."""
        from app.services.logger import ProxyLogger

        with patch('app.services.logger.get_settings', return_value=mock_settings):
            with patch('app.services.logger.TimedRotatingFileHandler'):
                with patch('app.services.logger.jsonlogger.JsonFormatter'):
                    logger = ProxyLogger()

                    sensitive_headers = {
                        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "password": "secret_password",
                        "client_secret": "very_long_secret_key_12345"
                    }

                    masked = logger._mask_sensitive_headers(sensitive_headers)

                    # Authorization debe estar enmascarado
                    assert masked["Authorization"] == "Bearer eyJ***"
                    assert masked["password"] == "***"
                    assert masked["client_secret"] == "very_long_s***"


# ============================================================================
# TESTS - CLIENTE GLPI (TC-02, TC-03, TC-18, TC-19)
# ============================================================================

class TestGLPIClient:
    """Tests para el cliente HTTP de GLPI."""

    @pytest.mark.asyncio
    async def test_check_connection_success(self, mock_settings, mock_oauth_manager):
        """TC-02: Verificar conexión con GLPI."""
        from app.services.glpi_client import GLPIClient

        client = GLPIClient()

        mock_response = Mock()
        mock_response.status_code = 200

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            result = await client.check_connection()

            assert result is True

    @pytest.mark.asyncio
    async def test_check_connection_failure(self, mock_settings, mock_oauth_manager):
        """TC-02: Verificar falla de conexión."""
        from app.services.glpi_client import GLPIClient

        client = GLPIClient()

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.request = AsyncMock(side_effect=Exception("Connection refused"))
            mock_get_client.return_value = mock_http_client

            result = await client.check_connection()

            assert result is False

    def test_build_headers(self, mock_settings, mock_oauth_manager):
        """TC-18: Verifica que headers obligatorios se agregan."""
        from app.services.glpi_client import GLPIClient

        client = GLPIClient()
        mock_oauth_manager.get_bearer_token_header.return_value = {}

        headers = client._build_headers()

        assert headers["Accept"] == "application/json"
        assert headers["GLPI-Entity-Recursive"] == "true"
        assert headers["Accept-Language"] == "en_GB"

    @pytest.mark.asyncio
    async def test_request_includes_bearer_token(self, mock_settings, mock_oauth_manager):
        """TC-18: Verifica inclusión de Bearer token."""
        from app.services.glpi_client import GLPIClient

        client = GLPIClient()
        mock_oauth_manager.get_bearer_token_header.return_value = {
            "Authorization": "Bearer test_token"
        }

        mock_response = Mock()
        mock_response.status_code = 200

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            await client.get("/api.php/v2.2/User")

            # Verificar que se llamó con el header de autorización
            call_args = mock_http_client.request.call_args
            headers = call_args.kwargs.get('headers', {})
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer test_token"


# ============================================================================
# TESTS - MODELOS (TC-04, TC-06)
# ============================================================================

class TestModels:
    """Tests para los modelos de datos."""

    def test_token_request_model(self):
        """Verifica modelo de request de token."""
        from app.models.token import TokenRequest

        request = TokenRequest(
            grant_type="password",
            client_id="test_client",
            client_secret="test_secret",
            username="test_user",
            password="test_pass"
        )

        assert request.grant_type == "password"
        assert request.client_id == "test_client"

    def test_token_response_model(self):
        """Verifica modelo de response de token."""
        from app.models.token import TokenResponse

        response = TokenResponse(
            access_token="token_123",
            expires_in=3600,
            token_type="Bearer"
        )

        assert response.access_token == "token_123"
        assert response.expires_in == 3600
        assert response.token_type == "Bearer"

    def test_health_response_model(self):
        """Verifica modelo de respuesta de health."""
        from app.models.requests import HealthResponse

        response = HealthResponse(
            status="healthy",
            glpi_connected=True,
            token_valid=True
        )

        assert response.status == "healthy"
        assert response.glpi_connected is True

    def test_error_response_model(self):
        """Verifica modelo de respuesta de error."""
        from app.models.token import ErrorResponse

        error = ErrorResponse(
            error="invalid_grant",
            error_description="Invalid credentials"
        )

        assert error.error == "invalid_grant"


# ============================================================================
# TESTS - MIDDLEWARE (TC-08, TC-09)
# ============================================================================

class TestMiddleware:
    """Tests para el middleware de logging."""

    @pytest.mark.asyncio
    async def test_logging_middleware_captures_request(self, mock_settings):
        """TC-08: Verifica que el middleware captura requests."""
        from app.middleware.logging import LoggingMiddleware
        from fastapi import FastAPI

        app = FastAPI()
        middleware = LoggingMiddleware(app)

        # Crear mock de request
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url.path = "/api/v2.2/test"
        mock_request.headers = {"content-type": "application/json"}
        mock_request.body = AsyncMock(return_value=b'{"test": "data"}')
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.100"

        # Mock de call_next
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.body = b'{"result": "ok"}'

        async def mock_call_next(req):
            return mock_response

        # Ejecutar middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verificar que response tiene request_id
        assert "X-Request-ID" in response.headers


# ============================================================================
# EJECUCIÓN DE TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])