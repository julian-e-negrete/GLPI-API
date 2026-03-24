"""
Convenience endpoints for ticket querying.
Adds server-side filtering by assigned_user and status on top of the generic proxy.
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
    List tickets with optional server-side filtering by assigned user and/or status.

    Query params:
    - assigned_id: filter tickets where a user with this ID has role 'assigned'
    - status_id:   1=New 2=Processing 4=Pending 5=Solved 6=Closed
    - start, limit: pagination
    """
    if not authorization:
        cached = oauth_manager.get_cached_token()
        if cached:
            authorization = f"Bearer {cached}"
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token required")

    headers = {"Authorization": authorization}

    response = await glpi_client.request(
        "GET", "/api.php/v2.2/Assistance/Ticket",
        params={"start": start, "limit": 200},
        headers=headers
    )

    if response.status_code != 200:
        return response.json()

    tickets = response.json()

    # Filter by status
    if status_id is not None:
        tickets = [
            t for t in tickets
            if (isinstance(t.get("status"), dict) and t["status"].get("id") == status_id)
            or t.get("status") == status_id
        ]

    # Filter by assigned user (requires per-ticket TeamMember lookup)
    if assigned_id is not None:
        filtered = []
        for ticket in tickets:
            tm_resp = await glpi_client.request(
                "GET", f"/api.php/v2.2/Assistance/Ticket/{ticket['id']}/TeamMember",
                headers=headers
            )
            if tm_resp.status_code == 200:
                members = tm_resp.json()
                if any(m.get("id") == assigned_id and m.get("role") == "assigned" for m in members):
                    filtered.append(ticket)
        tickets = filtered

    return tickets
