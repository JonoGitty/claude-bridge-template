"""
Claude Bridge Relay — lightweight HTTP server for direct LAN communication
between Claude Code instances on different machines.

Run on both machines:
  python relay/server.py

Listens on port 9111. Each instance can then:
  POST /message   — send a message to this device's inbox
  GET  /messages  — read all pending messages
  POST /ack       — acknowledge/clear a message by id
  GET  /ping      — health check
  GET  /profile   — returns this device's capability profile
"""

import http.server
import json
import os
import sys
import time
import uuid
import platform
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime

PORT = 9111
BRIDGE_DIR = Path(__file__).resolve().parent.parent
INBOX_DIR = BRIDGE_DIR / "relay" / "inbox"
DEVICES_DIR = BRIDGE_DIR / "devices"

# Auto-detect device name — override with BRIDGE_DEVICE env var
DEVICE_NAME = os.environ.get("BRIDGE_DEVICE") or (
    "windows" if platform.system() == "Windows" else "mac"
)

INBOX_DIR.mkdir(parents=True, exist_ok=True)


class RelayHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {args[0]}")

    def _respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/ping":
            self._respond(200, {
                "status": "ok",
                "device": DEVICE_NAME,
                "time": datetime.now().isoformat(),
            })

        elif path == "/messages":
            messages = []
            for f in sorted(INBOX_DIR.glob("*.json")):
                try:
                    msg = json.loads(f.read_text(encoding="utf-8"))
                    msg["_file"] = f.name
                    messages.append(msg)
                except Exception:
                    pass
            self._respond(200, {"messages": messages, "count": len(messages)})

        elif path == "/profile":
            profile_path = DEVICES_DIR / f"{DEVICE_NAME}.yml"
            if profile_path.exists():
                text = profile_path.read_text(encoding="utf-8")
                self._respond(200, {"device": DEVICE_NAME, "profile": text})
            else:
                self._respond(404, {"error": f"No profile found for {DEVICE_NAME}"})

        else:
            self._respond(404, {"error": "Not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode() if content_len else "{}"

        try:
            data = json.loads(body) if body.strip() else {}
        except json.JSONDecodeError:
            self._respond(400, {"error": "Invalid JSON"})
            return

        if path == "/message":
            msg_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
            msg = {
                "id": msg_id,
                "from": data.get("from", "unknown"),
                "to": DEVICE_NAME,
                "subject": data.get("subject", ""),
                "body": data.get("body", ""),
                "priority": data.get("priority", "normal"),
                "type": data.get("type", "info"),
                "timestamp": datetime.now().isoformat(),
            }
            msg_path = INBOX_DIR / f"{msg_id}.json"
            msg_path.write_text(json.dumps(msg, indent=2), encoding="utf-8")
            self._respond(200, {"status": "delivered", "id": msg_id})

        elif path == "/ack":
            msg_id = data.get("id", "")
            msg_file = INBOX_DIR / f"{msg_id}.json"
            if msg_file.exists():
                msg_file.unlink()
                self._respond(200, {"status": "acknowledged", "id": msg_id})
            else:
                self._respond(404, {"error": f"Message {msg_id} not found"})

        else:
            self._respond(404, {"error": "Not found"})


def main():
    print(f"Claude Bridge Relay — {DEVICE_NAME}")
    print(f"Listening on port {PORT}")
    print(f"Inbox: {INBOX_DIR}")
    print(f"Profile: {DEVICES_DIR / DEVICE_NAME}.yml")
    print()

    server = http.server.HTTPServer(("0.0.0.0", PORT), RelayHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
