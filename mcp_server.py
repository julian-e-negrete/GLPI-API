"""
GLPI API Proxy — MCP Server
Tools for interacting with GLPI through the proxy.
"""
import asyncio
import json
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource, Tool, TextContent,
    ListResourcesResult, ReadResourceResult,
    ListToolsResult, CallToolResult,
)

# ── Config ────────────────────────────────────────────────────────────────────
PROXY_URL     = "http://192.168.1.244:8080"
CLIENT_ID     = "ecd3715c5e6b2749bb592131721d154deb0d4823f6df547c3e617aa0a1679bcf"
CLIENT_SECRET = "2d4aa87d86ee7db68d1355aadcee595540ab9c25000a0cbbfe253e00f02f4ca7"
USERNAME      = "GLPI_PROXY"
PASSWORD      = "45237348"

server = Server("glpi-api-proxy")


# ── Auth ──────────────────────────────────────────────────────────────────────
def _get_token() -> str:
    r = httpx.post(f"{PROXY_URL}/api/v2.2/token", json={
        "grant_type": "password",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "username": USERNAME,
        "password": PASSWORD,
        "scope": "api user",
    }, timeout=15)
    return r.json()["access_token"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}


# ── Tools ─────────────────────────────────────────────────────────────────────
TOOLS = [
    Tool(
        name="proxy_health",
        description="Check proxy and GLPI connectivity. No auth required.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="list_users",
        description="List all GLPI users with their IDs and usernames.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="list_tickets",
        description="List tickets with optional filters.",
        inputSchema={
            "type": "object",
            "properties": {
                "status_id": {"type": "integer", "description": "1=New 2=Processing 4=Pending 5=Solved 6=Closed"},
                "assigned_id": {"type": "integer", "description": "Filter by assigned user ID"},
                "requester_id": {"type": "integer", "description": "Filter by requester user ID"},
                "limit": {"type": "integer", "default": 50},
                "start": {"type": "integer", "default": 0},
            },
        },
    ),
    Tool(
        name="get_ticket",
        description="Get full details of a ticket including timeline/followups.",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer"},
                "include_followups": {"type": "boolean", "default": False},
            },
            "required": ["ticket_id"],
        },
    ),
    Tool(
        name="create_ticket",
        description="Create a ticket with requester and assigned user.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "requester_id": {"type": "integer", "description": "User ID of who opens the ticket"},
                "assigned_id": {"type": "integer", "description": "User ID of who resolves the ticket"},
                "type": {"type": "integer", "description": "1=Incident 2=Request", "default": 1},
                "urgency": {"type": "integer", "description": "1=Very high 3=Medium 5=Very low", "default": 3},
            },
            "required": ["title", "content", "requester_id", "assigned_id"],
        },
    ),
    Tool(
        name="add_followup",
        description="Add a followup comment to a ticket.",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer"},
                "content": {"type": "string"},
                "is_private": {"type": "boolean", "default": False},
            },
            "required": ["ticket_id", "content"],
        },
    ),
    Tool(
        name="update_ticket_status",
        description="Update the status of a ticket. 1=New 2=Processing 4=Pending 5=Solved 6=Closed",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer"},
                "status_id": {"type": "integer"},
            },
            "required": ["ticket_id", "status_id"],
        },
    ),
    Tool(
        name="reassign_ticket",
        description="Reassign a ticket to a different user.",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer"},
                "assigned_id": {"type": "integer", "description": "New assigned user ID"},
            },
            "required": ["ticket_id", "assigned_id"],
        },
    ),
    Tool(
        name="glpi_get",
        description="GET any GLPI endpoint. Path example: /Administration/User or /Assistance/Ticket?limit=10",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="glpi_post",
        description="POST to any GLPI endpoint.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "body": {"type": "object"},
            },
            "required": ["path", "body"],
        },
    ),
    Tool(
        name="glpi_patch",
        description="PATCH any GLPI endpoint.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "body": {"type": "object"},
            },
            "required": ["path", "body"],
        },
    ),
    Tool(
        name="glpi_delete",
        description="DELETE any GLPI endpoint.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "force": {"type": "boolean", "default": False},
            },
            "required": ["path"],
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

    try:
        if name == "proxy_health":
            r = httpx.get(f"{PROXY_URL}/api/v2.2/Health", timeout=10)
            return ok(r.json())

        if name == "list_users":
            r = httpx.get(f"{PROXY_URL}/api/v2.2/Administration/User?limit=100",
                          headers=_headers(), timeout=15)
            users = [{"id": u["id"], "username": u["username"]} for u in r.json()]
            return ok(users)

        if name == "list_tickets":
            params = []
            if "status_id" in arguments:
                params.append(f"status_id={arguments['status_id']}")
            if "assigned_id" in arguments:
                params.append(f"assigned_id={arguments['assigned_id']}")
            if "requester_id" in arguments:
                params.append(f"requester_id={arguments['requester_id']}")
            params.append(f"limit={arguments.get('limit', 50)}")
            params.append(f"start={arguments.get('start', 0)}")
            qs = "&".join(params)
            r = httpx.get(f"{PROXY_URL}/api/v2.2/Tickets?{qs}", headers=_headers(), timeout=15)
            return ok(r.json())

        if name == "get_ticket":
            ticket_id = arguments["ticket_id"]
            h = _headers()
            r = httpx.get(f"{PROXY_URL}/api/v2.2/Assistance/Ticket/{ticket_id}", headers=h, timeout=15)
            result = r.json()
            if arguments.get("include_followups"):
                rf = httpx.get(f"{PROXY_URL}/api/v2.2/Assistance/Ticket/{ticket_id}/Timeline/Followup",
                               headers=h, timeout=15)
                result["followups"] = rf.json()
            return ok(result)

        if name == "create_ticket":
            r = httpx.post(f"{PROXY_URL}/api/v2.2/Tickets", headers=_headers(), json={
                "title": arguments["title"],
                "content": arguments["content"],
                "requester_id": arguments["requester_id"],
                "assigned_id": arguments["assigned_id"],
                "type": arguments.get("type", 1),
                "urgency": arguments.get("urgency", 3),
                "impact": arguments.get("urgency", 3),
                "priority": arguments.get("urgency", 3),
            }, timeout=15)
            return ok(r.json())

        if name == "add_followup":
            r = httpx.post(
                f"{PROXY_URL}/api/v2.2/Tickets/{arguments['ticket_id']}/followup",
                headers=_headers(),
                json={"content": arguments["content"], "is_private": arguments.get("is_private", False)},
                timeout=15,
            )
            return ok(r.json())

        if name == "update_ticket_status":
            r = httpx.patch(
                f"{PROXY_URL}/api/v2.2/Tickets/{arguments['ticket_id']}/status",
                headers=_headers(),
                json={"status_id": arguments["status_id"]},
                timeout=15,
            )
            return ok(r.json())

        if name == "reassign_ticket":
            ticket_id = arguments["ticket_id"]
            assigned_id = arguments["assigned_id"]
            h = _headers()
            httpx.delete(f"{PROXY_URL}/api/v2.2/Assistance/Ticket/{ticket_id}/TeamMember",
                         headers=h, json={"type": "User", "role": "assigned"}, timeout=15)
            r = httpx.post(f"{PROXY_URL}/api/v2.2/Assistance/Ticket/{ticket_id}/TeamMember",
                           headers=h, json={"type": "User", "id": assigned_id, "role": "assigned"}, timeout=15)
            return ok(r.json())

        if name == "glpi_get":
            r = httpx.get(f"{PROXY_URL}/api/v2.2{arguments['path']}", headers=_headers(), timeout=15)
            return ok(r.json())

        if name == "glpi_post":
            r = httpx.post(f"{PROXY_URL}/api/v2.2{arguments['path']}", headers=_headers(),
                           json=arguments["body"], timeout=15)
            return ok(r.json())

        if name == "glpi_patch":
            r = httpx.patch(f"{PROXY_URL}/api/v2.2{arguments['path']}", headers=_headers(),
                            json=arguments["body"], timeout=15)
            return ok(r.json())

        if name == "glpi_delete":
            path = arguments["path"]
            if arguments.get("force"):
                path += "?force=true"
            r = httpx.delete(f"{PROXY_URL}/api/v2.2{path}", headers=_headers(), timeout=15)
            return ok({"status": r.status_code, "body": r.text or "deleted"})

        return err(f"Unknown tool: {name}")

    except Exception as e:
        return err(str(e))


# ── Resources (docs) ──────────────────────────────────────────────────────────
RESOURCES = [
    Resource(uri="glpi://docs/endpoints", name="Proxy Endpoint Reference",
             description="All proxy endpoints and how to use them", mimeType="text/markdown"),
    Resource(uri="glpi://docs/rules", name="Agent Rules",
             description="Rules for agents using this proxy", mimeType="text/markdown"),
]


@server.list_resources()
async def list_resources() -> ListResourcesResult:
    return ListResourcesResult(resources=RESOURCES)


@server.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    import subprocess
    mapping = {
        "glpi://docs/endpoints": ("main", "PROXY_ENDPOINTS.md"),
        "glpi://docs/rules":     ("main", "AGENT_RULES.md"),
    }
    if uri not in mapping:
        return ReadResourceResult(contents=[TextContent(type="text", text=f"Unknown: {uri}")])
    branch, path = mapping[uri]
    result = subprocess.run(["git", "show", f"{branch}:{path}"],
                            cwd="/home/julian/programming/GLPI-API",
                            capture_output=True, text=True)
    return ReadResourceResult(contents=[TextContent(type="text", text=result.stdout)])


# ── Entry point ───────────────────────────────────────────────────────────────
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
