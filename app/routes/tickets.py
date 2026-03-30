"""
Ticket convenience endpoints.
- GET  /Tickets                          — filtered ticket list
- POST /Tickets                          — create ticket with requester + assigned in one call
- POST /Tickets/{id}/followup            — add followup
- PATCH /Tickets/{id}/status             — update status
"""
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Header, status
from pydantic import BaseModel
from app.services.glpi_client import glpi_client
from app.services.oauth import oauth_manager

router = APIRouter(prefix="/api/v2.2", tags=["Tickets"])


# ── Models ────────────────────────────────────────────────────────────────────

class CreateTicketRequest(BaseModel):
    title: str
    content: str
    requester_id: int
    assigned_id: int
    type: int = 1        # 1=Incident 2=Request
    urgency: int = 3
    impact: int = 3
    priority: int = 3


class FollowupRequest(BaseModel):
    content: str
    is_private: bool = False


class StatusUpdateRequest(BaseModel):
    status_id: int       # 1=New 2=Processing 4=Pending 5=Solved 6=Closed


# ── Helpers ───────────────────────────────────────────────────────────────────

def _auth_headers(authorization: Optional[str]) -> dict:
    if not authorization:
        cached = oauth_manager.get_cached_token()
        if cached:
            return {"Authorization": f"Bearer {cached}"}
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token required")
    return {"Authorization": authorization}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/Tickets")
async def list_tickets(
    request: Request,
    assigned_id: Optional[int] = None,
    requester_id: Optional[int] = None,
    status_id: Optional[int] = None,
    start: int = 0,
    limit: int = 50,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    List tickets with optional filtering.

    - status_id:    native GLPI RSQL filter (1=New 2=Processing 4=Pending 5=Solved 6=Closed)
    - assigned_id:  filter by assigned user (from team array)
    - requester_id: filter by requester user (from team array)
    - start, limit: pagination passed to GLPI
    """
    headers = _auth_headers(authorization)
    params = {"start": start, "limit": limit}
    if status_id is not None:
        params["filter"] = f"status.id=={status_id}"

    r = await glpi_client.request("GET", "/api.php/v2.2/Assistance/Ticket", params=params, headers=headers)
    if r.status_code != 200:
        return r.json()

    tickets = r.json()

    if assigned_id is not None:
        tickets = [t for t in tickets if any(
            m.get("id") == assigned_id and m.get("role") == "assigned"
            for m in (t.get("team") or [])
        )]

    if requester_id is not None:
        tickets = [t for t in tickets if any(
            m.get("id") == requester_id and m.get("role") == "requester"
            for m in (t.get("team") or [])
        )]

    return tickets


@router.post("/Tickets", status_code=201)
async def create_ticket(
    body: CreateTicketRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Create a ticket and assign requester + assigned in one call.

    - requester_id: user ID of who is opening the ticket
    - assigned_id:  user ID of who is responsible for it
    """
    headers = _auth_headers(authorization)

    # 1. Create ticket
    r = await glpi_client.request(
        "POST", "/api.php/v2.2/Assistance/Ticket",
        json_data={"name": body.title, "content": body.content,
                   "type": body.type, "urgency": body.urgency,
                   "impact": body.impact, "priority": body.priority},
        headers=headers
    )
    if r.status_code not in (200, 201):
        raise HTTPException(status_code=r.status_code, detail=r.json())

    ticket_id = r.json()["id"]

    # 2. Add requester
    await glpi_client.request(
        "POST", f"/api.php/v2.2/Assistance/Ticket/{ticket_id}/TeamMember",
        json_data={"type": "User", "id": body.requester_id, "role": "requester"},
        headers=headers
    )

    # 3. Add assigned
    await glpi_client.request(
        "POST", f"/api.php/v2.2/Assistance/Ticket/{ticket_id}/TeamMember",
        json_data={"type": "User", "id": body.assigned_id, "role": "assigned"},
        headers=headers
    )

    return {"id": ticket_id, "href": f"/Assistance/Ticket/{ticket_id}"}


@router.post("/Tickets/{ticket_id}/followup", status_code=201)
async def add_followup(
    ticket_id: int,
    body: FollowupRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """Add a followup comment to a ticket."""
    headers = _auth_headers(authorization)
    r = await glpi_client.request(
        "POST", f"/api.php/v2.2/Assistance/Ticket/{ticket_id}/Timeline/Followup",
        json_data={"content": body.content, "is_private": body.is_private},
        headers=headers
    )
    return r.json()


@router.patch("/Tickets/{ticket_id}/status")
async def update_status(
    ticket_id: int,
    body: StatusUpdateRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Update ticket status.
    1=New 2=Processing 4=Pending 5=Solved 6=Closed
    """
    headers = _auth_headers(authorization)
    r = await glpi_client.request(
        "PATCH", f"/api.php/v2.2/Assistance/Ticket/{ticket_id}",
        json_data={"status": {"id": body.status_id}},
        headers=headers
    )
    return r.json()
