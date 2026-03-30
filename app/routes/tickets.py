"""
Convenience endpoints for ticket querying.
- status_id is translated to a native GLPI RSQL filter (fast, server-side)
- assigned_id is filtered client-side using the 'team' array already in each ticket response
"""
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Header, status
from app.services.glpi_client import glpi_client
from app.services.oauth import oauth_manager

router = APIRouter(prefix="/api/v2.2", tags=["Tickets"])


@router.get("/Tickets")
async def list_tickets(
    request: Request,
    assigned_id: Optional[int] = None,
    status_id: Optional[int] = None,
    start: int = 0,
    limit: int = 50,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    List tickets filtered by status and/or assigned user.

    - status_id: passed as native RSQL filter to GLPI (1=New 2=Processing 4=Pending 5=Solved 6=Closed)
    - assigned_id: filtered client-side from the 'team' array in each ticket
    - start, limit: pagination passed to GLPI
    """
    if not authorization:
        cached = oauth_manager.get_cached_token()
        if cached:
            authorization = f"Bearer {cached}"
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token required")

    headers = {"Authorization": authorization}
    params = {"start": start, "limit": limit}

    if status_id is not None:
        params["filter"] = f"status.id=={status_id}"

    r = await glpi_client.request(
        "GET", "/api.php/v2.2/Assistance/Ticket",
        params=params,
        headers=headers
    )

    if r.status_code != 200:
        return r.json()

    tickets = r.json()

    if assigned_id is not None:
        tickets = [
            t for t in tickets
            if any(
                m.get("id") == assigned_id and m.get("role") == "assigned"
                for m in (t.get("team") or [])
            )
        ]

    return tickets
