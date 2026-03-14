# GLPI API — Lessons Learned & Integration Guide

Practical guide based on real testing against GLPI v2.2 through the proxy. Documents every gotcha discovered and how to make successful API calls.

---

## 1. The Scope Problem (Most Important)

### What happened

Every POST returned `403 ERROR_RIGHT_MISSING` even with a valid token and a Super-Admin user. The JWT payload showed `"scopes": []`.

### Root cause

GLPI only includes scopes in the token if you **explicitly request them** in the token request body. If you omit `scope`, GLPI issues a valid JWT with no scopes — and a scopeless token is rejected by every endpoint.

### Fix

Always send `scope` as part of the token request:

```bash
curl -X POST http://192.168.1.244/api/v2.2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&client_id=<id>&client_secret=<secret>&username=<user>&password=<pass>&scope=api user"
```

Or as JSON (proxy handles the conversion):

```json
{
  "grant_type": "password",
  "client_id": "<id>",
  "client_secret": "<secret>",
  "username": "<user>",
  "password": "<pass>",
  "scope": "api user"
}
```

### Available scopes

| Scope | Grants access to |
|---|---|
| `api` | All API endpoints (Tickets, Assets, Users, etc.) |
| `user` | `/Administration/User/Me` and user-related endpoints |
| `status` | `/status` endpoints only |
| `graphql` | `/GraphQL/` endpoint |
| `inventory` | Agent inventory submission |
| `email` | User's own email address |

**Rule**: for general API use, always request `scope=api user`.

### How to verify your token has scopes

Decode the JWT payload (middle segment, base64):

```python
import base64, json
token = "eyJ..."
payload = token.split('.')[1]
payload += '=' * (4 - len(payload) % 4)
print(json.loads(base64.b64decode(payload))['scopes'])
# Should be: ['api', 'user']  — NOT []
```

---

## 2. Token Request — Correct Format

### Critical: scope is ignored in JSON body sent to GLPI

GLPI's `/api.php/token` endpoint ignores the `scope` field when the body is `application/json`. It only processes `scope` from `application/x-www-form-urlencoded`.

The proxy's `/api/v2.2/token` endpoint handles this automatically — it always forwards to GLPI as form-urlencoded regardless of what format the client sends.

### Via the proxy (recommended)

```bash
# JSON body — proxy converts to form-urlencoded for GLPI
curl -X POST http://192.168.1.244/api/v2.2/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "password",
    "client_id": "<GLPI_CLIENT_ID>",
    "client_secret": "<GLPI_CLIENT_SECRET>",
    "username": "<user>",
    "password": "<pass>",
    "scope": "api user"
  }'
```

### Direct to GLPI (bypassing proxy)

```bash
curl -X POST http://192.168.1.33/api.php/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&client_id=<id>&client_secret=<secret>&username=<user>&password=<pass>&scope=api user"
```

### Response

```json
{
  "access_token": "eyJ...",
  "expires_in": 3600,
  "token_type": "Bearer",
  "refresh_token": "def502..."
}
```

---

## 3. Making Successful POST Requests

### Required headers for every request

```
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: application/json
GLPI-Entity-Recursive: true
Accept-Language: en_GB
```

The proxy adds `Accept`, `GLPI-Entity-Recursive`, and `Accept-Language` automatically. You only need to send `Authorization` and `Content-Type`.

### Create a Ticket

```bash
curl -X POST http://192.168.1.244/api/v2.2/Assistance/Ticket \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Printer not working",
    "content": "The printer on floor 1 is jammed.",
    "type": 1,
    "urgency": 3,
    "impact": 3,
    "priority": 3
  }'
```

**Ticket field reference**

| Field | Type | Values |
|---|---|---|
| `name` | string | Title of the ticket |
| `content` | string | Description (required) |
| `type` | int | `1` = Incident, `2` = Request |
| `urgency` | int | `1`=Very High, `2`=High, `3`=Medium, `4`=Low, `5`=Very Low |
| `impact` | int | Same scale as urgency |
| `priority` | int | Same scale as urgency |
| `status` | int | `1`=New, `2`=In Progress, `4`=Pending, `5`=Solved, `6`=Closed |

**Success response**
```json
{ "id": 42, "href": "/Assistance/Ticket/42" }
```

### Add a Followup to a Ticket

```bash
curl -X POST http://192.168.1.244/api/v2.2/Assistance/Ticket/42/Timeline/Followup \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{ "content": "Checked the issue. Waiting for user confirmation." }'
```

### Add a Task to a Ticket

```bash
curl -X POST http://192.168.1.244/api/v2.2/Assistance/Ticket/42/Timeline/Task \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{ "content": "Order replacement part from supplier." }'
```

### Create a User

```bash
curl -X POST http://192.168.1.244/api/v2.2/Administration/User \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john.smith",
    "firstname": "John",
    "realname": "Smith",
    "password": "SecurePass1!",
    "password2": "SecurePass1!"
  }'
```

> **Note**: GLPI uses `username` (not `name`) for the login field. The username must follow GLPI's validation rules — alphanumeric with dots/underscores/hyphens allowed.

### Create a Group

```bash
curl -X POST http://192.168.1.244/api/v2.2/Administration/Group \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{ "name": "IT Support", "comment": "First-level helpdesk" }'
```

### Create a Computer (Asset)

```bash
curl -X POST http://192.168.1.244/api/v2.2/Assets/Computer \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "WS-JSMITH-01",
    "serial": "SN-20240101",
    "otherserial": "INV-001",
    "comment": "John Smith workstation"
  }'
```

### Create a Location (Dropdown)

```bash
curl -X POST http://192.168.1.244/api/v2.2/Dropdowns/Location \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{ "name": "Server Room", "comment": "Main data center room" }'
```

---

## 4. Common Errors and Fixes

| Error | Cause | Fix |
|---|---|---|
| `ERROR_RIGHT_MISSING` + `"scopes": []` in JWT | Token requested without `scope` field | Add `"scope": "api user"` to token request |
| `ERROR_RIGHT_MISSING` + scopes present | User profile lacks write rights in GLPI | Set user profile to Super-Admin in GLPI UI |
| `Failed to create item` — "nombre de usuario no válido" | Used `name` instead of `username` for User creation | Use `username` field |
| `Failed to create item` — "ya está resuelto" | Ticket already has a solution | Don't add a second solution; use Followup instead |
| `500` on duplicate creation | Item with same name already exists | Check before creating, or use unique names |
| `502 Bad Gateway` | Proxy can't reach GLPI server | Check GLPI is running at `192.168.1.33` |
| `401 Unauthorized` | No token or expired token | Re-authenticate via `/api/v2.2/token` |

---

## 5. Postman Setup

### Environment variables

| Variable | Value |
|---|---|
| `proxy_url` | `http://192.168.1.244` |
| `token` | *(set after auth request)* |
| `client_id` | `5880211c...` |
| `client_secret` | `b6d8fbdc...` |

### Auth request (run first, save token)

- Method: `POST`
- URL: `{{proxy_url}}/api/v2.2/token`
- Body (JSON):
```json
{
  "grant_type": "password",
  "client_id": "{{client_id}}",
  "client_secret": "{{client_secret}}",
  "username": "HaraiDasan",
  "password": "45237348",
  "scope": "api user"
}
```
- In **Tests** tab, add:
```javascript
pm.environment.set("token", pm.response.json().access_token);
```

### All subsequent requests

- Authorization tab → Bearer Token → `{{token}}`

---

## 6. Mock Data Created (2026-03-14)

The following data was seeded via `seed_mock_data.py`:

### Groups
- IT Support, Network Ops, Sysadmins, Management

### Users
- `john.smith` (John Smith)
- `maria.garcia` (Maria Garcia)
- `r.lopez` (Roberto Lopez)
- `ana.morales` (Ana Morales)
- `c.perez` (Carlos Perez)

### Locations
- HQ - Floor 1, HQ - Floor 2, Server Room, Branch Office

### Assets
- **Computers**: WS-JSMITH-01, WS-MGARCIA-01, SRV-FILE-01, SRV-WEB-01, LAPTOP-RLOPEZ
- **Printers**: PRN-FLOOR1-01, PRN-FLOOR2-01
- **Network**: SW-CORE-01, SW-FLOOR1, FW-EDGE-01

### Tickets
| # | Title | Type | Priority | Status |
|---|---|---|---|---|
| 1 | Cannot connect to VPN | Incident | High | In Progress |
| 2 | Request new laptop for new hire | Request | Medium | New |
| 3 | Printer PRN-FLOOR1-01 paper jam | Incident | Low | In Progress |
| 4 | Email server slow response | Incident | Very High | In Progress |
| 5 | Install Adobe Acrobat on WS-MGARCIA-01 | Request | Very Low | Solved |
| 6 | Network outage - Branch Office | Incident | Very High | In Progress |
| 7 | Reset password for cperez | Request | High | Solved |
| 8 | SRV-FILE-01 disk space critical | Incident | Very High | In Progress |
