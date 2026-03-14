# MCP Server — Setup & Usage Guide

This project includes an MCP (Model Context Protocol) server that exposes the proxy documentation and live GLPI tools directly inside Kiro.

---

## What is it?

The MCP server (`mcp_server.py`) lets Kiro:
- Read documentation from the `docs/proxy-setup` and `docs/api-testing` branches as resources
- Make live calls to the GLPI proxy (GET, POST, DELETE) as tools
- Check proxy health, get tokens, list endpoints — all from within the chat

---

## How to activate it

The config is already in `.kiro/settings/mcp.json`. Just start Kiro from this project directory:

```bash
cd /home/haraidasan/programming/GLPI-API
kiro-cli chat
```

Kiro auto-detects `.kiro/settings/mcp.json` on startup and loads the server. No manual steps needed.

---

## Available Resources

Read-only docs pulled live from git branches:

| Resource URI | Branch | File |
|---|---|---|
| `glpi://docs/readme` | `docs/proxy-setup` | `README.md` — setup guide & API usage |
| `glpi://docs/spec` | `docs/proxy-setup` | `SPEC.md` — full endpoint catalog |
| `glpi://docs/lessons` | `docs/api-testing` | `LESSONS_LEARNED.md` — integration guide |
| `glpi://docs/seed-script` | `docs/api-testing` | `seed_mock_data.py` — mock data seeder |
| `glpi://docs/seed-results` | `docs/api-testing` | `seed_results.json` — last seed run |

---

## Available Tools

Live calls to the proxy at `http://192.168.1.244`:

| Tool | What it does |
|---|---|
| `proxy_health` | Check proxy and GLPI connection status |
| `get_token` | Obtain a fresh Bearer token from GLPI |
| `glpi_get` | GET any GLPI resource (e.g. `/Assistance/Ticket`) |
| `glpi_post` | POST/create any resource with a JSON body |
| `glpi_delete` | DELETE a resource by path (e.g. `/Assistance/Ticket/42`) |
| `list_endpoints` | List all GLPI v2.2 endpoint categories |

---

## Example prompts inside Kiro

Once the MCP server is loaded, just ask naturally:

```
"Get all tickets from GLPI"
"Create a ticket for a printer issue on floor 1"
"Delete ticket 42"
"Check proxy health"
"Show me the lessons learned doc"
"What endpoints are available?"
"Show me the full SPEC"
```

Kiro will call the appropriate tool or read the resource automatically.

---

## Manual run (for debugging)

```bash
source /home/haraidasan/programming/python/.venv/bin/activate
python3 mcp_server.py
```

It waits on stdin/stdout (correct MCP behavior). Use Ctrl+C to stop.

---

## Config file

`.kiro/settings/mcp.json`:
```json
{
  "mcpServers": {
    "glpi-api-proxy": {
      "command": "/home/haraidasan/programming/python/.venv/bin/python3",
      "args": ["/home/haraidasan/programming/GLPI-API/mcp_server.py"]
    }
  }
}
```

To point to a different proxy, edit `PROXY_URL` and `GLPI_URL` at the top of `mcp_server.py`.

---

## Dependencies

Already installed in the venv:
```
mcp
httpx
```

To reinstall:
```bash
source /home/haraidasan/programming/python/.venv/bin/activate
pip install mcp httpx
```
