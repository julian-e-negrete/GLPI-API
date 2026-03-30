# GLPI API Proxy — Endpoint Reference

Base URL: `http://192.168.1.244:8080`

All endpoints except `/`, `/api/v2.2/ping`, and `/api/v2.2/Health` require:
```
Authorization: Bearer <token>
```

---

## Authentication

### `POST /api/v2.2/token`

Obtain a Bearer token. Accepts `application/json` or `application/x-www-form-urlencoded`.

**Body**
```json
{
  "grant_type": "password",
  "client_id": "<client_id>",
  "client_secret": "<client_secret>",
  "username": "<username>",
  "password": "<password>",
  "scope": "api user"
}
```

> `scope: "api user"` is mandatory. Omitting it causes all subsequent calls to return `403`.

**Response `200`**
```json
{ "access_token": "eyJ...", "expires_in": 3600, "token_type": "Bearer", "scope": null }
```

| Code | Reason |
|---|---|
| `400` | `grant_type` is not `"password"` |
| `401` | Wrong credentials |
| `422` | Missing required fields |

---

## Health

### `GET /api/v2.2/ping`

Liveness check. No auth required.

**Response `200`**
```json
{ "service": "glpi-api-proxy", "status": "ok", "version": "1.0.0" }
```

---

### `GET /api/v2.2/Health`

Proxy health + GLPI connectivity check. No auth required.

**Response `200`**
```json
{
  "status": "healthy",
  "service": "glpi-api-proxy",
  "version": "1.0.0",
  "glpi_connected": true,
  "token_valid": true
}
```

`status` is `"degraded"` if GLPI is unreachable. `token_valid` is `null` if no token has been obtained yet.

---

## Tickets (proxy convenience layer)

### `GET /api/v2.2/Tickets`

List tickets with optional filtering. Combines native GLPI RSQL filtering (for status) with client-side filtering (for assigned user).

**Query params**

| Param | Type | Description |
|---|---|---|
| `status_id` | int | Filter by status. Passed as native RSQL `filter=status.id==N` to GLPI. |
| `assigned_id` | int | Filter by assigned user ID. Filtered from the `team` array in each ticket. |
| `start` | int | Pagination offset (default `0`) |
| `limit` | int | Page size (default `50`) |

**Status values**

| ID | Meaning |
|---|---|
| `1` | New |
| `2` | Processing (assigned) |
| `4` | Pending |
| `5` | Solved |
| `6` | Closed |

**Example — tickets assigned to GLPI_PROXY (id=14) in progress**
```
GET /api/v2.2/Tickets?assigned_id=14&status_id=2
```

**Response** — array of ticket objects (same schema as GLPI's `/Assistance/Ticket`).

---

## Generic GLPI Proxy

### `GET|POST|PUT|PATCH|DELETE /api/v2.2/{resource}`

Transparent proxy to any GLPI v2.2 endpoint. Forwards method, query params, body, and the following headers:

| Header forwarded | Description |
|---|---|
| `Authorization` | Bearer token |
| `GLPI-Entity` | Scope to entity ID |
| `GLPI-Profile` | Use specific profile |
| `GLPI-Entity-Recursive` | Include child entities (`"true"/"false"`) |
| `Accept-Language` | Response language |

If `Authorization` is omitted and a valid token is cached in memory, the proxy uses it automatically.

**Path mapping**: `{resource}` → `/api.php/v2.2/{resource}` on GLPI.

**Common query params (all GET list endpoints)**

| Param | Description |
|---|---|
| `filter` | RSQL query string (e.g. `status.id==2`) |
| `start` | Pagination offset |
| `limit` | Page size |
| `sort` | `property:asc` or `property:desc` |

**Common query params (DELETE)**

| Param | Description |
|---|---|
| `force` | `true` = permanent delete, `false` = move to trash |

**Errors**

| Code | Reason |
|---|---|
| `401` | No token and no cached token |
| `502` | GLPI server unreachable |

---

## Infrastructure (server inventory)

### `POST /api/v2.2/infra/computers`

Register a server as a Computer asset in GLPI (upsert by name).

**Body**
```json
{
  "name": "SRV-SCRAPING-PROXY",
  "ip_local": "192.168.1.244",
  "ip_tailscale": "100.112.16.115",
  "role": "scraping-proxy",
  "databases": [
    { "name": "marketdata-pg", "port": 5432, "version": "PostgreSQL", "comment": "..." }
  ],
  "note": "Free-text note attached to the computer"
}
```

---

### `GET /api/v2.2/infra/computers`

List all Computer assets registered in GLPI.

---

### `POST /api/v2.2/infra/seed`

Seed the two known servers (`SRV-SCRAPING-PROXY`, `SRV-GLPI-PROCESSOR`) into GLPI with their full configuration.

---

### `POST /api/v2.2/infra/servers/{server_name}/tickets`

Create a ticket linked to a server.

**Body**
```json
{
  "title": "Task title",
  "description": "Full description",
  "agent": "kiro",
  "urgency": 3
}
```

Urgency: `1`=Very high → `5`=Very low.

---

### `GET /api/v2.2/infra/servers/{server_name}/tickets`

List all active tickets for a server.

---

### `PATCH /api/v2.2/infra/servers/{server_name}/tickets/{ticket_id}/complete`

Mark a ticket as solved.

**Body**
```json
{ "solution": "Description of what was done." }
```

---

### `POST /api/v2.2/infra/servers/{server_name}/tickets/{ticket_id}/followup`

Add a followup comment to a ticket without closing it.

**Body**
```json
{ "content": "Update text." }
```

---

## Service info

### `GET /`

```json
{
  "service": "GLPI API Proxy",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs",
  "health": "/api/v2.2/Health",
  "glpi_server": "http://192.168.1.33:80"
}
```

Interactive docs: `http://192.168.1.244:8080/docs`
