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

    try:
        return await oauth_manager.get_token(
            username=body.username,
            password=body.password,
            client_id=body.client_id,
            client_secret=body.client_secret,
            scope=body.scope or "api user",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"Error de autenticación: {str(e)}")
