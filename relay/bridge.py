"""
Claude Bridge Client — communicate with the other device's relay server.

Usage:
  python relay/bridge.py ping                            # Check if other device is up
  python relay/bridge.py send "subject" "body"           # Send a message
  python relay/bridge.py read                            # Read pending messages on THIS device
  python relay/bridge.py profile                         # Get other device's capability profile
  python relay/bridge.py ack <message_id>                # Acknowledge/clear a message
  python relay/bridge.py send-task "subject" "body"      # Send a task request
  python relay/bridge.py send-question "subject" "body"  # Send a question
  python relay/bridge.py prompt "do something"           # Auto-processed by watcher on other device

Configuration:
  Set BRIDGE_PEER environment variable to the other device's relay URL.
  Example: BRIDGE_PEER=http://192.168.0.100:9111

  Or edit the PEERS dict below with your device IPs/hostnames.
"""

import json
import os
import sys
import platform
from urllib.request import urlopen, Request
from urllib.error import URLError

# ──────────────────────────────────────────────────────────────
# CONFIGURE THESE for your setup.
# Map: from THIS device's perspective, where is the OTHER device?
# ──────────────────────────────────────────────────────────────
PEERS = {
    # "windows": "http://<mac-ip-or-hostname>:9111",
    # "mac": "http://<windows-ip-or-hostname>:9111",
}

PEER_HOSTNAMES = {
    # Fallback mDNS hostnames
    # "windows": "http://my-mac.local:9111",
    # "mac": "http://my-windows-pc.local:9111",
}

DEVICE = os.environ.get("BRIDGE_DEVICE") or (
    "windows" if platform.system() == "Windows" else "mac"
)
LOCAL_URL = "http://localhost:9111"


def get_peer_url():
    """Find the other device's relay URL. Checks env var, then PEERS dict, then hostnames."""
    # Check env var first
    env_peer = os.environ.get("BRIDGE_PEER")
    if env_peer and _try_url(env_peer):
        return env_peer

    # Try configured IPs
    url = PEERS.get(DEVICE)
    if url and _try_url(url):
        return url

    # Try hostnames
    url = PEER_HOSTNAMES.get(DEVICE)
    if url and _try_url(url):
        return url

    print("ERROR: Cannot reach peer device.")
    print("  Is relay/server.py running on the other machine?")
    print("  Set BRIDGE_PEER=http://<other-device-ip>:9111 or edit PEERS in bridge.py")
    sys.exit(1)


def _try_url(url):
    try:
        urlopen(f"{url}/ping", timeout=3)
        return True
    except Exception:
        return False


def _get(url):
    try:
        resp = urlopen(url, timeout=10)
        return json.loads(resp.read().decode())
    except URLError as e:
        return {"error": str(e)}


def _post(url, data):
    try:
        req = Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
        resp = urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except URLError as e:
        return {"error": str(e)}


def cmd_ping():
    peer = get_peer_url()
    result = _get(f"{peer}/ping")
    print(json.dumps(result, indent=2))


def cmd_send(subject, body, msg_type="info"):
    peer = get_peer_url()
    result = _post(f"{peer}/message", {
        "from": DEVICE,
        "subject": subject,
        "body": body,
        "type": msg_type,
    })
    print(json.dumps(result, indent=2))


def cmd_read():
    """Read messages in THIS device's local inbox."""
    result = _get(f"{LOCAL_URL}/messages")
    if "error" in result:
        print(f"ERROR: Is relay/server.py running locally? {result['error']}")
        return
    msgs = result.get("messages", [])
    if not msgs:
        print("No pending messages.")
        return
    for msg in msgs:
        print(f"\n{'='*60}")
        print(f"  ID:       {msg['id']}")
        print(f"  From:     {msg['from']}")
        print(f"  Type:     {msg['type']}")
        print(f"  Priority: {msg['priority']}")
        print(f"  Time:     {msg['timestamp']}")
        print(f"  Subject:  {msg['subject']}")
        print(f"  Body:     {msg['body']}")
    print(f"\n{'='*60}")
    print(f"Total: {len(msgs)} message(s)")


def cmd_profile():
    peer = get_peer_url()
    result = _get(f"{peer}/profile")
    if "profile" in result:
        print(f"--- {result['device']} profile ---")
        print(result["profile"])
    else:
        print(json.dumps(result, indent=2))


def cmd_ack(msg_id):
    result = _post(f"{LOCAL_URL}/ack", {"id": msg_id})
    print(json.dumps(result, indent=2))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "ping":
        cmd_ping()
    elif cmd == "send":
        if len(sys.argv) < 4:
            print("Usage: bridge.py send \"subject\" \"body\"")
            sys.exit(1)
        cmd_send(sys.argv[2], sys.argv[3])
    elif cmd == "send-task":
        if len(sys.argv) < 4:
            print("Usage: bridge.py send-task \"subject\" \"body\"")
            sys.exit(1)
        cmd_send(sys.argv[2], sys.argv[3], msg_type="task-request")
    elif cmd == "send-question":
        if len(sys.argv) < 4:
            print("Usage: bridge.py send-question \"subject\" \"body\"")
            sys.exit(1)
        cmd_send(sys.argv[2], sys.argv[3], msg_type="question")
    elif cmd == "prompt":
        prompt_text = " ".join(sys.argv[2:])
        if not prompt_text:
            print("Usage: bridge.py prompt \"your prompt for the other Claude\"")
            sys.exit(1)
        cmd_send("prompt", prompt_text, msg_type="prompt")
    elif cmd == "read":
        cmd_read()
    elif cmd == "profile":
        cmd_profile()
    elif cmd == "ack":
        if len(sys.argv) < 3:
            print("Usage: bridge.py ack <message_id>")
            sys.exit(1)
        cmd_ack(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
