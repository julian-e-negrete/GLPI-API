from fastapi import APIRouter, HTTPException, Form, Request, status
from typing import Optional

from app.services.oauth import oauth_manager
from app.models.token import TokenResponse, TokenRequest


router = APIRouter(prefix="/api/v2.2", tags=["Authentication"])


async def _parse_token_request(request: Request) -> TokenRequest:
    """Acepta tanto JSON como form-urlencoded."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)
    return TokenRequest(**data)


@router.post("/token", response_model=TokenResponse)
async def get_token(request: Request):
    try:
        body = await _parse_token_request(request)
    except Exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Parámetros requeridos: grant_type, client_id, client_secret, username, password")

    if body.grant_type != "password":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="grant_type debe ser 'password'")

    from app.config import get_settings
    settings = get_settings()

    if body.client_id != settings.glpi_client_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="client_id inválido")

    if body.client_secret != settings.glpi_client_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="client_secret inválido")

    try:
        return await oauth_manager.get_token(
            username=body.username,
            password=body.password,
            scope=body.scope or "api user"
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"Error de autenticación: {str(e)}")
