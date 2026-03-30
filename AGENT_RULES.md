# GLPI Proxy — Agent Rules for Ticket Creation

These rules must be followed by any agent using this proxy to interact with GLPI.

---

## Proxy Agent Identity

The proxy authenticates to GLPI using the `GLPI_PROXY` user (id=`14`). This is a service account used only for authentication — it has no default role in tickets.

Roles are always determined by the use case:
- The **caller** (the agent or user making the request to the proxy) is the `requester`
- The **target** (who the ticket is directed to) is `assigned`
- `GLPI_PROXY` may appear as `assigned` only if a ticket is opened about a proxy malfunction

---

## Proxy Base URL

```
http://192.168.1.244:8080/api/v2.2
```

> **CRITICAL**: All requests — including token acquisition — go through the proxy.  
> Never call `http://192.168.1.33` directly. That is the internal GLPI server and is not accessible to agents.  
> The only valid entry point is `http://192.168.1.244:8080`.

### Connectivity check (no auth required)

Before any operation, verify the proxy is up:
```
GET http://192.168.1.244:8080/api/v2.2/ping
```
Expected response: `{"service": "glpi-api-proxy", "status": "ok", "version": "1.0.0"}`

If this times out or fails → proxy is down, do not attempt any further calls.

---

## Step 1 — Authenticate

Always request a token before any operation. Include `scope: "api user"` or GLPI will reject the request.

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

Each user object has `id` (numeric) and `username` (login name).

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

Response: `{ "id": <ticket_id>, "href": "..." }`. Save the `id`.

---

## Step 4 — Assign Actors via TeamMember

The ticket body does NOT set requester/assigned. Always call TeamMember after creation.

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
| `requester` | Solicitante | Who is opening the ticket |
| `assigned` | Asignado a | Who is responsible for resolving it |
| `observer` | Observador | CC / watcher |

---

## Observer Policy

Every ticket created via the proxy **automatically** includes **HaraiDasan (id=7)** as observer. This is enforced server-side — clients do not need to add it manually.

---

## Full Flow Summary

```
1. POST /token                                  → get access_token
2. GET  /Administration/User?limit=100          → resolve user IDs
3. POST /Assistance/Ticket                      → create ticket, get ticket_id
4. POST /Assistance/Ticket/{id}/TeamMember      → add requester (the caller)
5. POST /Assistance/Ticket/{id}/TeamMember      → add assigned (the target)
```

---

## ITIL Workflow Endpoints (Problem, Change, Task)

Use these when the situation calls for more than a simple ticket:

| Situation | Endpoint | When to use |
|---|---|---|
| Recurring incident | `POST /Assistance/Problem` | Same issue keeps happening |
| Planned fix / service change | `POST /Assistance/Change` | Before applying a code fix or restart |
| Scheduled maintenance | `POST /Project/Task` | Recurring checks, maintenance windows |

### Problem

```
GET    /Assistance/Problem
POST   /Assistance/Problem
GET    /Assistance/Problem/{id}
PATCH  /Assistance/Problem/{id}
GET    /Assistance/Problem/{id}/Timeline/Followup
POST   /Assistance/Problem/{id}/Timeline/Followup
```

### Change

```
GET    /Assistance/Change
POST   /Assistance/Change
GET    /Assistance/Change/{id}
PATCH  /Assistance/Change/{id}
GET    /Assistance/Change/{id}/Timeline/Followup
POST   /Assistance/Change/{id}/Timeline/Followup
```

### Task

```
GET    /Project/Task
POST   /Project/Task
GET    /Project/Task/{id}
PATCH  /Project/Task/{id}
```

TeamMember (requester/assigned/observer) works the same way on Problem and Change as on Ticket.

---

## Reading & Replying to Tickets

```
# List tickets assigned to you (filter server-side)
GET /Tickets?assigned_id={your_user_id}&status_id={status}

# Read full ticket
GET /Assistance/Ticket/{id}

# Read conversation thread
GET /Assistance/Ticket/{id}/Timeline/Followup

# Post a reply
POST /Assistance/Ticket/{id}/Timeline/Followup
{ "content": "<text>", "is_private": false }

# Update status
PATCH /Assistance/Ticket/{id}
{ "status": {"id": 5} }
```

Status IDs: `1`=New `2`=Processing `4`=Pending `5`=Solved `6`=Closed

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
| `type` | int | `1`=Incident `2`=Request |
| `urgency` | int | `1`=Very low `2`=Low `3`=Medium `4`=High `5`=Very high |
| `impact` | int | same scale as urgency |
| `priority` | int | same scale as urgency |
| `status` | int | `1`=New `2`=Processing `4`=Pending `5`=Solved `6`=Closed |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ping` times out | Proxy is down | Do not proceed. Report the issue. |
| `ping` OK but `/token` times out | Agent is calling GLPI directly | Use `http://192.168.1.244:8080` for ALL calls |
| `401` on any endpoint | Token missing or expired | Re-authenticate via `POST /token` with `scope: "api user"` |
| `403 ERROR_RIGHT_MISSING` | Token was issued without `api user` scope | Re-authenticate and explicitly include `"scope": "api user"` in the token request body |
| Empty ticket list | Wrong `assigned_id` or `status_id` | Use `GET /Tickets` without filters first to confirm tickets exist |

### Correct token request (copy-paste ready)

```
POST http://192.168.1.244:8080/api/v2.2/token
Content-Type: application/json

{
  "grant_type": "password",
  "client_id": "<client_id>",
  "client_secret": "<client_secret>",
  "username": "<username>",
  "password": "<password>",
  "scope": "api user"
}
```

The `scope` field is **mandatory**. Omitting it causes all GLPI API calls to return `403`.
