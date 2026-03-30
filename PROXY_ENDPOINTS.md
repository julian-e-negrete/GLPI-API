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

List tickets with optional filtering.

**Query params**

| Param | Type | Description |
|---|---|---|
| `status_id` | int | Native RSQL filter. 1=New 2=Processing 4=Pending 5=Solved 6=Closed |
| `assigned_id` | int | Filter by assigned user ID (from `team` array) |
| `requester_id` | int | Filter by requester user ID (from `team` array) |
| `start` | int | Pagination offset (default `0`) |
| `limit` | int | Page size (default `50`) |

---

### `POST /api/v2.2/Tickets`

Create a ticket with requester and assigned user set in one call.

**Body**
```json
{
  "title": "Ticket title",
  "content": "Description",
  "requester_id": 14,
  "assigned_id": 13,
  "type": 1,
  "urgency": 3,
  "impact": 3,
  "priority": 3
}
```

`type`: 1=Incident, 2=Request. Urgency/impact/priority: 1=Very high → 5=Very low.

---

### `POST /api/v2.2/Tickets/{id}/followup`

Add a followup comment to a ticket.

**Body**
```json
{ "content": "Comment text.", "is_private": false }
```

---

### `PATCH /api/v2.2/Tickets/{id}/status`

Update ticket status.

**Body**
```json
{ "status_id": 5 }
```

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
