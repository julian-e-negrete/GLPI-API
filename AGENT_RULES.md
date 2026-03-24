# GLPI Proxy — Agent Rules for Ticket Creation

These rules must be followed by any agent using this proxy to interact with GLPI.

---

## Proxy Base URL

```
http://192.168.1.38:8080/api/v2.2
```

---

## Step 1 — Authenticate

Always request a token before any operation. Include `scope: "api user"` or it will be rejected by GLPI.

```
POST /token
Content-Type: application/json

{
  "grant_type": "password",
  "client_id": "<your_client_id>",
  "client_secret": "<your_client_secret>",
  "username": "<your_glpi_username>",
  "password": "<your_glpi_password>",
  "scope": "api user"
}
```

Store the returned `access_token` and use it in all subsequent requests as:
```
Authorization: Bearer <access_token>
```

---

## Step 2 — Resolve User IDs

Before creating a ticket, resolve the numeric IDs of the users involved.

```
GET /Administration/User?limit=100
Authorization: Bearer <token>
```

Each user object has:
- `id` — numeric ID used in all API calls
- `username` — the login name

Alternatively look up by username:
```
GET /Administration/User/username/{username}
```

---

## Step 3 — Create the Ticket

```
POST /Assistance/Ticket
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "<ticket title>",
  "content": "<ticket description>",
  "type": 1,
  "urgency": 3,
  "impact": 3,
  "priority": 3
}
```

The response returns `{ "id": <ticket_id>, "href": "..." }`. Save the `id`.

---

## Step 4 — Assign Actors via TeamMember

**This is mandatory.** The ticket body does NOT set requester/assigned. You must call TeamMember after creation.

```
POST /Assistance/Ticket/{ticket_id}/TeamMember
Authorization: Bearer <token>
Content-Type: application/json

{
  "type": "User",
  "id": <user_id>,
  "role": "<role>"
}
```

Valid roles:
| Role | GLPI field | Meaning |
|---|---|---|
| `requester` | Solicitante | Who is opening/requesting the ticket |
| `assigned` | Asignado a | Who is responsible for resolving it |
| `observer` | Observador | CC / watcher |

### Role convention

- The **agent making the request** (the one authenticated via the proxy) → `requester`
- The **target user or system** the ticket is directed to → `assigned`

### Example

Agent `GLPI_PROXY` (id=14) creates a ticket directed to `AlgoTrade Server` (id=13):

```json
// Requester — the agent itself
{ "type": "User", "id": 14, "role": "requester" }

// Assigned — the target
{ "type": "User", "id": 13, "role": "assigned" }
```

---

## Full Flow Summary

```
1. POST /token                                  → get access_token
2. GET  /Administration/User?limit=100          → resolve user IDs
3. POST /Assistance/Ticket                      → create ticket, get ticket_id
4. POST /Assistance/Ticket/{id}/TeamMember      → add requester (yourself)
5. POST /Assistance/Ticket/{id}/TeamMember      → add assigned (target user)
```

---

## Optional Headers (forwarded to GLPI)

| Header | Type | Description |
|---|---|---|
| `GLPI-Entity` | integer | Scope to a specific entity ID |
| `GLPI-Profile` | integer | Use a specific profile |
| `GLPI-Entity-Recursive` | `"true"/"false"` | Include child entities |
| `Accept-Language` | string | Response language (e.g. `en_GB`) |

---

## Ticket Field Reference

| Field | Type | Values |
|---|---|---|
| `type` | int | `1` = Incident, `2` = Request |
| `urgency` | int | `1`=Very low `2`=Low `3`=Medium `4`=High `5`=Very high |
| `impact` | int | same scale as urgency |
| `priority` | int | same scale as urgency |
| `status` | int | `1`=New `2`=Processing(assigned) `3`=Processing(planned) `4`=Pending `5`=Solved `6`=Closed |
