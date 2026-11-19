import json, sys, urllib.request
# usage: python fx.py file_with_code.py  -> runs code inside Fusion via local MCP add-in
URL = "http://127.0.0.1:8765/mcp"
code = open(sys.argv[1], encoding="utf-8").read()
def post(payload, sid=None):
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if sid: h["Mcp-Session-Id"] = sid
    r = urllib.request.urlopen(urllib.request.Request(URL, json.dumps(payload).encode(), h), timeout=600)
    return r.headers.get("Mcp-Session-Id"), r.read().decode()
sid, _ = post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "drawtest", "version": "0"}}})
try: post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
except Exception: pass
_, out = post({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "execute_python", "arguments": {"code": code, "session_id": "drawtest", "persistent": True, "description": "drawing tool test"}}}, sid)
print(out[-6000:])
