"""
Claude Bridge Watcher — automatically processes incoming relay messages
by feeding them into Claude Code CLI and sending responses back.

This lets two Claude instances prompt each other without human intervention.

Usage:
  python relay/watcher.py              # Watch and auto-respond
  python relay/watcher.py --dry-run    # Show what would happen without executing
  python relay/watcher.py --interval 5 # Poll every 5 seconds (default: 10)

How it works:
  1. Polls the local relay inbox for new messages
  2. When a prompt/task/question arrives, pipes it to: claude -p (via stdin)
  3. Captures Claude's response
  4. Sends the response back to the sender via the relay
  5. Acknowledges the original message

Important notes:
  - Claude is run from a TEMP directory, not the bridge repo. This prevents
    Claude from reading the bridge's CLAUDE.md and getting confused.
  - The prompt is piped via stdin, not as a CLI argument, to avoid shell
    escaping issues (especially on Windows).
  - The claude binary is auto-detected via PATH and common install locations.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import platform
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

BRIDGE_DIR = Path(__file__).resolve().parent.parent
INBOX_DIR = BRIDGE_DIR / "relay" / "inbox"
DEVICE = os.environ.get("BRIDGE_DEVICE") or (
    "windows" if platform.system() == "Windows" else "mac"
)
LOCAL_URL = "http://localhost:9111"
POLL_INTERVAL = 10  # seconds

# Message types that trigger auto-processing
AUTO_PROCESS_TYPES = {"task-request", "question", "prompt"}

# Track processed messages to avoid re-processing
PROCESSED_FILE = BRIDGE_DIR / "relay" / ".processed"


def _find_claude():
    """Find the claude CLI binary, checking common locations."""
    found = shutil.which("claude")
    if found:
        return found
    candidates = []
    if platform.system() == "Windows":
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, ".claude", "local", "claude.exe"),
            os.path.join(home, ".local", "bin", "claude.cmd"),
            os.path.join(home, "AppData", "Roaming", "npm", "claude.cmd"),
            os.path.join(home, "AppData", "Local", "Programs", "claude", "claude.exe"),
        ]
    else:
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, ".local", "bin", "claude"),
            os.path.join(home, ".claude", "local", "claude"),
            "/usr/local/bin/claude",
            "/opt/homebrew/bin/claude",
        ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return "claude"


CLAUDE_BIN = _find_claude()


def get_peer_url():
    """Find the other device's relay URL."""
    env_peer = os.environ.get("BRIDGE_PEER")
    if env_peer and _try_url(env_peer):
        return env_peer
    return None


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
        req = Request(url, data=json.dumps(data).encode(),
                      headers={"Content-Type": "application/json"})
        resp = urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except URLError as e:
        return {"error": str(e)}


def load_processed():
    """Load set of already-processed message IDs."""
    if PROCESSED_FILE.exists():
        return set(PROCESSED_FILE.read_text(encoding="utf-8").strip().split("\n"))
    return set()


def mark_processed(msg_id):
    """Mark a message as processed."""
    processed = load_processed()
    processed.add(msg_id)
    recent = sorted(processed)[-500:]
    PROCESSED_FILE.write_text("\n".join(recent), encoding="utf-8")


def run_claude(prompt):
    """Run claude -p with the prompt piped via stdin. Returns response text."""
    # Run from temp dir to avoid CLAUDE.md contamination
    neutral_dir = tempfile.gettempdir()
    cmd = [CLAUDE_BIN, "-p"]

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=neutral_dir,
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"[Claude returned error code {result.returncode}]\n{result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "[Claude timed out after 5 minutes]"
    except FileNotFoundError:
        return "[Error: 'claude' CLI not found in PATH]"


def process_message(msg, dry_run=False):
    """Process a single incoming message."""
    msg_id = msg.get("id", "unknown")
    sender = msg.get("from", "unknown")
    msg_type = msg.get("type", "info")
    subject = msg.get("subject", "")
    body = msg.get("body", "")

    prompt = f"""You are responding to a message from the {sender} device via the Claude Bridge relay.
Your text output will be automatically sent back as a reply — just write your response directly.
Do NOT attempt to use tools, read files, or run commands unless the message explicitly asks you to perform a task that requires them.

Subject: {subject}

{body}"""

    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] Processing: [{msg_type}] {subject} (from {sender})")

    if dry_run:
        print(f"  [DRY RUN] Would run claude -p with the above prompt")
        print(f"  [DRY RUN] Would send response back to {sender}")
        return

    print(f"  Running Claude...")
    response = run_claude(prompt)
    print(f"  Got response ({len(response)} chars)")

    # Send response back to sender
    peer_url = get_peer_url()
    if peer_url:
        result = _post(f"{peer_url}/message", {
            "from": DEVICE,
            "subject": f"Re: {subject}",
            "body": response,
            "type": "response",
        })
        if "error" not in result:
            print(f"  Response sent to {sender}")
        else:
            print(f"  WARNING: Failed to send response: {result['error']}")
    else:
        print(f"  WARNING: Peer not reachable — saving response locally")
        resp_file = INBOX_DIR / f"unsent_response_{msg_id}.json"
        resp_file.write_text(json.dumps({
            "to": sender,
            "subject": f"Re: {subject}",
            "body": response,
            "type": "response",
        }, indent=2), encoding="utf-8")

    # Acknowledge the original message
    _post(f"{LOCAL_URL}/ack", {"id": msg_id})
    mark_processed(msg_id)


def watch(dry_run=False, interval=POLL_INTERVAL):
    """Main watch loop."""
    print(f"Claude Bridge Watcher — {DEVICE}")
    print(f"Claude binary: {CLAUDE_BIN}")
    print(f"Polling inbox every {interval}s")
    print(f"Auto-processing message types: {', '.join(sorted(AUTO_PROCESS_TYPES))}")
    if dry_run:
        print("DRY RUN MODE — no actions will be taken")
    print()

    processed = load_processed()

    while True:
        try:
            result = _get(f"{LOCAL_URL}/messages")

            if "error" not in result:
                messages = result.get("messages", [])
                for msg in messages:
                    msg_id = msg.get("id", "")
                    msg_type = msg.get("type", "")

                    if msg_id in processed:
                        continue

                    if msg_type in AUTO_PROCESS_TYPES:
                        process_message(msg, dry_run=dry_run)
                        processed.add(msg_id)
                    else:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] Received [{msg_type}]: {msg.get('subject', '')} — skipping auto-process")
                        mark_processed(msg_id)
                        processed.add(msg_id)

        except Exception as e:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Error: {e}")

        time.sleep(interval)


def main():
    dry_run = "--dry-run" in sys.argv
    interval = POLL_INTERVAL

    if "--interval" in sys.argv:
        idx = sys.argv.index("--interval")
        if idx + 1 < len(sys.argv):
            interval = int(sys.argv[idx + 1])

    watch(dry_run=dry_run, interval=interval)


if __name__ == "__main__":
    main()
