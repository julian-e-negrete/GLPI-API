"""
GLPI API Proxy — MCP Server
Exposes proxy documentation, GLPI endpoint catalog, lessons learned,
and live proxy tools as MCP resources and tools.
"""
import asyncio
import json
import subprocess
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource, Tool, TextContent,
    ListResourcesResult, ReadResourceResult,
    ListToolsResult, CallToolResult,
)

# ── Config ────────────────────────────────────────────────────────────────────
PROXY_URL   = "http://192.168.1.244"
GLPI_URL    = "http://192.168.1.33"
CLIENT_ID   = "5880211c5e72134f1ae47dda08377e4b503bd3d15f93d858dda5ab82a4a000e0"
CLIENT_SECRET = "b6d8fbdc08f6443abce916dae0d5184f56793a50782130e3c6fa6153692d165c"
USERNAME    = "HaraiDasan"
PASSWORD    = "45237348"
REPO_PATH   = "/home/haraidasan/programming/GLPI-API"

server = Server("glpi-api-proxy")


def _git_file(branch: str, path: str) -> str:
    """Read a file from a git branch without checking it out."""
    result = subprocess.run(
        ["git", "show", f"{branch}:{path}"],
        cwd=REPO_PATH, capture_output=True, text=True
    )
    return result.stdout if result.returncode == 0 else f"[File not found: {branch}:{path}]"


def _get_token() -> str:
    r = httpx.post(
        f"{GLPI_URL}/api.php/token",
        data={
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "username": USERNAME,
            "password": PASSWORD,
            "scope": "api user",
        },
        timeout=15,
    )
    return r.json()["access_token"]


# ── Resources ─────────────────────────────────────────────────────────────────
RESOURCES = [
    Resource(
        uri="glpi://docs/readme",
        name="README — Proxy Setup & API Usage",
        description="Full setup guide, endpoint reference and usage examples (docs/proxy-setup branch)",
        mimeType="text/markdown",
    ),
    Resource(
        uri="glpi://docs/spec",
        name="SPEC — Technical Specification",
        description="Architecture, OAuth flow, all GLPI v2.2 endpoints catalog (docs/proxy-setup branch)",
        mimeType="text/markdown",
    ),
    Resource(
        uri="glpi://docs/lessons",
        name="Lessons Learned — Integration Guide",
        description="Scope gotchas, correct POST formats, Postman setup, error reference (docs/api-testing branch)",
        mimeType="text/markdown",
    ),
    Resource(
        uri="glpi://docs/seed-script",
        name="Seed Script — Mock Data",
        description="Python script that populates GLPI with realistic test data (docs/api-testing branch)",
        mimeType="text/x-python",
    ),
    Resource(
        uri="glpi://docs/seed-results",
        name="Seed Results — Last Run",
        description="JSON results of the last mock data seeding run (docs/api-testing branch)",
        mimeType="application/json",
    ),
]


@server.list_resources()
async def list_resources() -> ListResourcesResult:
    return ListResourcesResult(resources=RESOURCES)


@server.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    mapping = {
        "glpi://docs/readme":       ("docs/proxy-setup", "README.md"),
        "glpi://docs/spec":         ("docs/proxy-setup", "SPEC.md"),
        "glpi://docs/lessons":      ("docs/api-testing", "LESSONS_LEARNED.md"),
        "glpi://docs/seed-script":  ("docs/api-testing", "seed_mock_data.py"),
        "glpi://docs/seed-results": ("docs/api-testing", "seed_results.json"),
    }
    if uri not in mapping:
        return ReadResourceResult(contents=[TextContent(type="text", text=f"Unknown resource: {uri}")])
    branch, path = mapping[uri]
    content = _git_file(branch, path)
    return ReadResourceResult(contents=[TextContent(type="text", text=content)])


# ── Tools ─────────────────────────────────────────────────────────────────────
TOOLS = [
    Tool(
        name="proxy_health",
        description="Check the health of the GLPI API proxy and its connection to GLPI.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="glpi_get",
        description="Make a GET request to any GLPI endpoint through the proxy. Example path: /Assistance/Ticket",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "GLPI resource path, e.g. /Assistance/Ticket or /Administration/User"}
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="glpi_post",
        description="Create a resource in GLPI via POST through the proxy.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "GLPI resource path, e.g. /Assistance/Ticket"},
                "body": {"type": "object", "description": "JSON body for the POST request"},
            },
            "required": ["path", "body"],
        },
    ),
    Tool(
        name="glpi_delete",
        description="Delete a resource in GLPI via DELETE through the proxy.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Full resource path with ID, e.g. /Assistance/Ticket/42"},
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="get_token",
        description="Obtain a fresh Bearer token from GLPI via the proxy.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="list_endpoints",
        description="List all available GLPI v2.2 endpoint categories.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="create_server_ticket",
        description=(
            "Create a GLPI ticket linked to a server (Computer asset). "
            "Use this when starting a task on a server to register it in GLPI. "
            "server_name must be one of: SRV-SCRAPING-PROXY, SRV-GLPI-PROCESSOR"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "server_name": {"type": "string", "description": "Server name, e.g. SRV-SCRAPING-PROXY"},
                "title": {"type": "string", "description": "Short task title"},
                "description": {"type": "string", "description": "Full task description"},
                "agent": {"type": "string", "description": "Agent name creating the ticket", "default": "kiro"},
                "urgency": {"type": "integer", "description": "1=very high, 2=high, 3=medium, 4=low, 5=very low", "default": 3},
            },
            "required": ["server_name", "title", "description"],
        },
    ),
    Tool(
        name="list_server_tickets",
        description="List all active GLPI tickets linked to a server.",
        inputSchema={
            "type": "object",
            "properties": {
                "server_name": {"type": "string", "description": "Server name, e.g. SRV-GLPI-PROCESSOR"},
            },
            "required": ["server_name"],
        },
    ),
    Tool(
        name="complete_server_ticket",
        description=(
            "Mark a GLPI ticket as resolved. "
            "Use this when a task on a server is finished."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "server_name": {"type": "string", "description": "Server name the ticket belongs to"},
                "ticket_id": {"type": "integer", "description": "GLPI ticket ID to resolve"},
                "solution": {"type": "string", "description": "Description of what was done", "default": "Tarea completada por agente."},
            },
            "required": ["server_name", "ticket_id"],
        },
    ),
    Tool(
        name="glpi_patch",
        description="Update a resource in GLPI via PATCH through the proxy.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Full resource path with ID, e.g. /Assistance/Ticket/42"},
                "body": {"type": "object", "description": "JSON body with fields to update"},
            },
            "required": ["path", "body"],
        },
    ),
]


@server.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(tools=TOOLS)


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    def ok(data) -> CallToolResult:
        text = json.dumps(data, indent=2, ensure_ascii=False) if not isinstance(data, str) else data
        return CallToolResult(content=[TextContent(type="text", text=text)])

    def err(msg: str) -> CallToolResult:
        return CallToolResult(content=[TextContent(type="text", text=f"Error: {msg}")], isError=True)

    if name == "proxy_health":
        try:
            r = httpx.get(f"{PROXY_URL}/api/v2.2/Health", timeout=10)
            return ok(r.json())
        except Exception as e:
            return err(str(e))

    if name == "get_token":
        try:
            token = _get_token()
            return ok({"access_token": token[:40] + "...", "note": "Full token available for use in other tools"})
        except Exception as e:
            return err(str(e))

    if name == "glpi_get":
        path = arguments.get("path", "")
        try:
            token = _get_token()
            r = httpx.get(
                f"{PROXY_URL}/api/v2.2{path}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            return ok(r.json())
        except Exception as e:
            return err(str(e))

    if name == "glpi_post":
        path = arguments.get("path", "")
        body = arguments.get("body", {})
        try:
            token = _get_token()
            r = httpx.post(
                f"{PROXY_URL}/api/v2.2{path}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=body,
                timeout=15,
            )
            return ok(r.json())
        except Exception as e:
            return err(str(e))

    if name == "glpi_delete":
        path = arguments.get("path", "")
        try:
            token = _get_token()
            r = httpx.delete(
                f"{PROXY_URL}/api/v2.2{path}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            return ok({"status": r.status_code, "body": r.text or "deleted"})
        except Exception as e:
            return err(str(e))

    if name == "list_endpoints":
        categories = [
            "Administration: /User, /Group, /Entity, /Profile, /EventLog",
            "Assistance:     /Ticket, /Problem, /Change, /RecurringTicket",
            "Assets:         /Computer, /Monitor, /Printer, /Phone, /NetworkEquipment, /Software, /Rack, ...",
            "Components:     /Processor, /Memory, /HardDrive, /NetworkCard, ...",
            "Management:     /Budget, /Contract, /Supplier, /Document, /Domain, /Cluster, ...",
            "Dropdowns:      /Location, /ITILCategory, /State, /Manufacturer, ...",
            "Knowledgebase:  /Article, /Category",
            "Project:        /Project, /Task",
            "Tools:          /Reminder, /RSSFeed",
            "Setup:          /Config, /LDAPDirectory",
            "Rule:           /Collection/{collection}/Rule",
            "GraphQL:        /GraphQL/",
            "Status:         /status, /status/all",
        ]
        return ok("\n".join(categories))

    if name == "glpi_patch":
        path = arguments.get("path", "")
        body = arguments.get("body", {})
        try:
            token = _get_token()
            r = httpx.patch(
                f"{PROXY_URL}/api/v2.2{path}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=body,
                timeout=15,
            )
            try:
                return ok(r.json())
            except Exception:
                return ok({"status": r.status_code, "body": r.text or "ok"})
        except Exception as e:
            return err(str(e))

    if name == "create_server_ticket":
        server_name = arguments.get("server_name", "")
        try:
            token = _get_token()
            r = httpx.post(
                f"{PROXY_URL}/api/v2.2/infra/servers/{server_name}/tickets",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "title": arguments["title"],
                    "description": arguments["description"],
                    "agent": arguments.get("agent", "kiro"),
                    "urgency": arguments.get("urgency", 3),
                },
                timeout=15,
            )
            return ok(r.json())
        except Exception as e:
            return err(str(e))

    if name == "list_server_tickets":
        server_name = arguments.get("server_name", "")
        try:
            token = _get_token()
            r = httpx.get(
                f"{PROXY_URL}/api/v2.2/infra/servers/{server_name}/tickets",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            return ok(r.json())
        except Exception as e:
            return err(str(e))

    if name == "complete_server_ticket":
        server_name = arguments.get("server_name", "")
        ticket_id = arguments.get("ticket_id")
        try:
            token = _get_token()
            r = httpx.patch(
                f"{PROXY_URL}/api/v2.2/infra/servers/{server_name}/tickets/{ticket_id}/complete",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"solution": arguments.get("solution", "Tarea completada por agente.")},
                timeout=15,
            )
            try:
                return ok(r.json())
            except Exception:
                return ok({"status": r.status_code, "body": r.text or "ok"})
        except Exception as e:
            return err(str(e))

    return err(f"Unknown tool: {name}")


# ── Entry point ───────────────────────────────────────────────────────────────
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
