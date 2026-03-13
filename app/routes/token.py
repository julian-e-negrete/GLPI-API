"""
Rutas para autenticación OAuth.
Maneja la obtención de tokens de acceso.
"""
from fastapi import APIRouter, HTTPException, Form, status
from typing import Optional

from app.services.oauth import oauth_manager
from app.models.token import TokenResponse


router = APIRouter(prefix="/api/v2.2", tags=["Authentication"])


@router.post("/token", response_model=TokenResponse)
async def get_token(
    grant_type: str = Form(default="password", description="Tipo de grant OAuth"),
    client_id: str = Form(..., description="ID de cliente OAuth"),
    client_secret: str = Form(..., description="Secreto del cliente"),
    username: str = Form(..., description="Usuario GLPI"),
    password: str = Form(..., description="Password del usuario")
):
    """
    Obtiene un token de acceso usando el grant de password.

    Este endpoint permite obtener un token de acceso OAuth para autenticar
    las peticionessubsecuentes a la API de GLPI.

    ## Parámetros (form-urlencoded)

    - **grant_type**: Debe ser "password"
    - **client_id**: ID de cliente OAuth (proporcionado por GLPI)
    - **client_secret**: Secreto del cliente OAuth
    - **username**: Usuario de GLPI
    - **password**: Password del usuario de GLPI
    """
    # Validar grant_type
    if grant_type != "password":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="grant_type debe ser 'password'"
        )

    # Validar credenciales de cliente
    from app.config import get_settings
    settings = get_settings()

    if client_id != settings.glpi_client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="client_id inválido"
        )

    if client_secret != settings.glpi_client_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="client_secret inválido"
        )

    try:
        # Obtener token
        token_response = await oauth_manager.get_token(
            username=username,
            password=password
        )
        return token_response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error de autenticación: {str(e)}"
        )