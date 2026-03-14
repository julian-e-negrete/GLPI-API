"""
GLPI Mock Data Seeder
Creates realistic sample data via the proxy at 192.168.1.244:8080
Results are logged to seed_results.json
"""
import json
import httpx
import sys
from datetime import datetime

PROXY = "http://192.168.1.244/api/v2.2"
CLIENT_ID = "5880211c5e72134f1ae47dda08377e4b503bd3d15f93d858dda5ab82a4a000e0"
CLIENT_SECRET = "b6d8fbdc08f6443abce916dae0d5184f56793a50782130e3c6fa6153692d165c"
USERNAME = "HaraiDasan"
PASSWORD = "45237348"

results = []


def log(label, method, path, status, body):
    entry = {"label": label, "method": method, "path": path, "status": status, "response": body}
    results.append(entry)
    ok = "✓" if status and status < 300 else "✗"
    print(f"  {ok} [{status}] {method} {path}  — {label}")


def post(client, path, payload, label):
    try:
        r = client.post(f"{PROXY}{path}", json=payload)
        body = r.json() if r.content else {}
        log(label, "POST", path, r.status_code, body)
        return body if r.status_code < 300 else None
    except Exception as e:
        log(label, "POST", path, None, str(e))
        return None


def get(client, path, label):
    try:
        r = client.get(f"{PROXY}{path}")
        body = r.json() if r.content else {}
        log(label, "GET", path, r.status_code, body)
        return body if r.status_code < 300 else None
    except Exception as e:
        log(label, "GET", path, None, str(e))
        return None


# ── 1. Token ──────────────────────────────────────────────────────────────────
print("\n── Authenticating ──")
try:
    # Must be sent directly to GLPI as form-urlencoded with explicit scope
    r = httpx.post("http://192.168.1.33/api.php/token", data={
        "grant_type": "password",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "username": USERNAME,
        "password": PASSWORD,
        "scope": "api user",
    }, timeout=15)
    token_data = r.json()
    token = token_data.get("access_token")
    if not token:
        print(f"✗ Could not get token: {token_data}")
        sys.exit(1)
    print(f"  ✓ Token obtained (expires in {token_data.get('expires_in')}s)")
except Exception as e:
    print(f"✗ Connection failed: {e}")
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}"}
client = httpx.Client(headers=headers, timeout=20)

# ── 2. Groups ─────────────────────────────────────────────────────────────────
print("\n── Creating Groups ──")
groups_data = [
    {"name": "IT Support",      "comment": "First-level helpdesk team"},
    {"name": "Network Ops",     "comment": "Network infrastructure team"},
    {"name": "Sysadmins",       "comment": "Server and systems administration"},
    {"name": "Management",      "comment": "Management and supervisors"},
]
group_ids = []
for g in groups_data:
    res = post(client, "/Administration/Group", g, f"Group: {g['name']}")
    if res and res.get("id"):
        group_ids.append(res["id"])

# ── 3. Users ──────────────────────────────────────────────────────────────────
print("\n── Creating Users ──")
users_data = [
    {"username": "john.smith",   "firstname": "John",    "realname": "Smith",   "password": "Pass1234!", "password2": "Pass1234!"},
    {"username": "maria.garcia", "firstname": "Maria",   "realname": "Garcia",  "password": "Pass1234!", "password2": "Pass1234!"},
    {"username": "r.lopez",      "firstname": "Roberto", "realname": "Lopez",   "password": "Pass1234!", "password2": "Pass1234!"},
    {"username": "ana.morales",  "firstname": "Ana",     "realname": "Morales", "password": "Pass1234!", "password2": "Pass1234!"},
    {"username": "c.perez",      "firstname": "Carlos",  "realname": "Perez",   "password": "Pass1234!", "password2": "Pass1234!"},
]
user_ids = []
for u in users_data:
    res = post(client, "/Administration/User", u, f"User: {u['username']}")
    if res and res.get("id"):
        user_ids.append(res["id"])

# ── 4. Locations ──────────────────────────────────────────────────────────────
print("\n── Creating Locations ──")
locations = [
    {"name": "HQ - Floor 1", "comment": "Main office, ground floor"},
    {"name": "HQ - Floor 2", "comment": "Main office, second floor"},
    {"name": "Server Room",  "comment": "Main data center room"},
    {"name": "Branch Office","comment": "Remote branch location"},
]
location_ids = []
for loc in locations:
    res = post(client, "/Dropdowns/Location", loc, f"Location: {loc['name']}")
    if res and res.get("id"):
        location_ids.append(res["id"])

# ── 5. Computers ──────────────────────────────────────────────────────────────
print("\n── Creating Computers ──")
computers = [
    {"name": "WS-JSMITH-01",  "serial": "SN-20240101", "otherserial": "INV-001", "comment": "John Smith workstation"},
    {"name": "WS-MGARCIA-01", "serial": "SN-20240102", "otherserial": "INV-002", "comment": "Maria Garcia workstation"},
    {"name": "SRV-FILE-01",   "serial": "SN-20240201", "otherserial": "INV-010", "comment": "File server"},
    {"name": "SRV-WEB-01",    "serial": "SN-20240202", "otherserial": "INV-011", "comment": "Web server"},
    {"name": "LAPTOP-RLOPEZ", "serial": "SN-20240103", "otherserial": "INV-003", "comment": "Roberto Lopez laptop"},
]
for c in computers:
    post(client, "/Assets/Computer", c, f"Computer: {c['name']}")

# ── 6. Printers ───────────────────────────────────────────────────────────────
print("\n── Creating Printers ──")
printers = [
    {"name": "PRN-FLOOR1-01", "serial": "PRN-SN-001", "comment": "HP LaserJet - Floor 1"},
    {"name": "PRN-FLOOR2-01", "serial": "PRN-SN-002", "comment": "Canon - Floor 2"},
]
for p in printers:
    post(client, "/Assets/Printer", p, f"Printer: {p['name']}")

# ── 7. Network Equipment ──────────────────────────────────────────────────────
print("\n── Creating Network Equipment ──")
netdevices = [
    {"name": "SW-CORE-01",  "serial": "NET-SN-001", "comment": "Core switch - Server Room"},
    {"name": "SW-FLOOR1",   "serial": "NET-SN-002", "comment": "Access switch - Floor 1"},
    {"name": "FW-EDGE-01",  "serial": "NET-SN-003", "comment": "Edge firewall"},
]
for n in netdevices:
    post(client, "/Assets/NetworkEquipment", n, f"NetworkEquipment: {n['name']}")

# ── 8. Tickets ────────────────────────────────────────────────────────────────
print("\n── Creating Tickets ──")
# type: 1=Incident, 2=Request | urgency/impact/priority: 1=Very High … 5=Very Low
tickets = [
    {
        "name": "Cannot connect to VPN",
        "content": "User jsmith reports VPN client fails to connect since this morning. Error: 'Authentication failed'.",
        "type": 1, "urgency": 2, "impact": 2, "priority": 2,
        "status": 2,  # In progress
    },
    {
        "name": "Request new laptop for new hire",
        "content": "New employee Ana Morales starts Monday. Needs a laptop with standard software package.",
        "type": 2, "urgency": 3, "impact": 3, "priority": 3,
        "status": 1,  # New
    },
    {
        "name": "Printer PRN-FLOOR1-01 paper jam",
        "content": "The printer on floor 1 has a recurring paper jam. Already cleared twice today.",
        "type": 1, "urgency": 3, "impact": 4, "priority": 4,
        "status": 2,
    },
    {
        "name": "Email server slow response",
        "content": "Multiple users report email client taking 30+ seconds to load inbox. Started after last night's update.",
        "type": 1, "urgency": 1, "impact": 1, "priority": 1,
        "status": 2,
    },
    {
        "name": "Install Adobe Acrobat on WS-MGARCIA-01",
        "content": "Maria Garcia needs Adobe Acrobat Pro for contract review work.",
        "type": 2, "urgency": 4, "impact": 5, "priority": 5,
        "status": 5,  # Solved
    },
    {
        "name": "Network outage - Branch Office",
        "content": "Branch office has no internet connectivity. All users affected. ISP ticket opened.",
        "type": 1, "urgency": 1, "impact": 1, "priority": 1,
        "status": 2,
    },
    {
        "name": "Reset password for cperez",
        "content": "User Carlos Perez locked out after too many failed login attempts.",
        "type": 2, "urgency": 2, "impact": 3, "priority": 3,
        "status": 5,  # Solved
    },
    {
        "name": "SRV-FILE-01 disk space critical",
        "content": "File server disk usage at 94%. Immediate cleanup or expansion required.",
        "type": 1, "urgency": 1, "impact": 2, "priority": 1,
        "status": 2,
    },
]
ticket_ids = []
for t in tickets:
    res = post(client, "/Assistance/Ticket", t, f"Ticket: {t['name'][:45]}")
    if res and res.get("id"):
        ticket_ids.append(res["id"])

# ── 9. Followups on first open ticket ────────────────────────────────────────
print("\n── Adding Followups ──")
if ticket_ids:
    tid = ticket_ids[0]
    followups = [
        {"content": "Checked VPN logs. Authentication request is reaching the server but failing at credential validation."},
        {"content": "Asked user to reset password via self-service portal. Waiting for confirmation."},
    ]
    for f in followups:
        post(client, f"/Assistance/Ticket/{tid}/Timeline/Followup", f, f"Followup on ticket {tid}")

# ── 10. Tasks on second ticket ───────────────────────────────────────────────
print("\n── Adding Tasks ──")
if len(ticket_ids) > 1:
    tid2 = ticket_ids[1]
    post(client, f"/Assistance/Ticket/{tid2}/Timeline/Task",
         {"content": "Order laptop from supplier. Model: Dell Latitude 5540."},
         f"Task on ticket {tid2}")

# ── 11. Verify health ─────────────────────────────────────────────────────────
print("\n── Proxy Health Check ──")
get(client, "/Health", "Health check")

# ── Save results ──────────────────────────────────────────────────────────────
client.close()
output = {
    "seeded_at": datetime.utcnow().isoformat() + "Z",
    "proxy": PROXY,
    "summary": {
        "groups_created": len(group_ids),
        "users_created": len(user_ids),
        "locations_created": len(location_ids),
        "tickets_created": len(ticket_ids),
    },
    "created_ids": {
        "groups": group_ids,
        "users": user_ids,
        "locations": location_ids,
        "tickets": ticket_ids,
    },
    "results": results,
}

with open("seed_results.json", "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n── Done ──")
print(f"  Groups:    {output['summary']['groups_created']}")
print(f"  Users:     {output['summary']['users_created']}")
print(f"  Locations: {output['summary']['locations_created']}")
print(f"  Tickets:   {output['summary']['tickets_created']}")
print(f"  Full results saved to seed_results.json\n")
