# Claude Bridge

**A private communication bridge between Claude Code instances running on different machines.**

If you run [Claude Code](https://docs.anthropic.com/en/docs/claude-code) on multiple devices (e.g. a Windows desktop and a Mac), they have no way to coordinate. Claude Bridge solves this with a shared private Git repo and an optional LAN relay for real-time communication.

Each device registers a **capability profile** — what OS it runs, what tools are installed, what projects live there, and what it's best at. When you give either instance a task, it can check the other device's profile and decide whether to handle it locally or delegate.

**Two communication modes:**
- **Git messages** — durable, works across any network, version-controlled
- **LAN relay** — instant, real-time, works over direct ethernet or local network. Includes an autonomous **watcher** that lets both Claude instances prompt each other without human intervention.

---

## How It Works

```
┌─────────────────┐                              ┌─────────────────┐
│   Device A      │         ┌──────────┐         │   Device B      │
│   (e.g. Mac)    │         │  GitHub   │         │  (e.g. Windows) │
│                 │  push/  │  (private │  push/  │                 │
│  Claude Code ◄──┼────────►│   repo)   │◄───────┼──► Claude Code  │
│                 │  pull   └──────────┘  pull   │                 │
│                 │                              │                 │
│  relay:9111 ◄───┼──────── ethernet/LAN ───────►┼──► relay:9111   │
│  watcher ◄──────┼──── autonomous prompting ───►┼──► watcher      │
└─────────────────┘                              └─────────────────┘
```

---

## Quick Start

### 1. Create your private bridge repo

```bash
gh repo create my-claude-bridge --private --clone
cd my-claude-bridge
```

### 2. Copy the template files

```bash
git clone https://github.com/JonoGitty/claude-bridge-template.git
cp -r claude-bridge-template/* my-claude-bridge/
cp claude-bridge-template/.gitignore my-claude-bridge/
cd my-claude-bridge
git add -A && git commit -m "Initial bridge setup" && git push
```

### 3. Set up Device A

Clone your private repo and create a device profile:

```bash
gh repo clone your-username/my-claude-bridge
cd my-claude-bridge
cp devices/example.yml devices/mac.yml  # or windows.yml, linux.yml, etc.
```

Edit the device profile with your machine's capabilities (see [devices/example.yml](devices/example.yml) for the full format).

### 4. Set up Device B

Repeat on the second machine with its own device profile.

### 5. Done (basic mode)

Both Claude Code instances can now read each other's profiles, route tasks, and leave Git messages. For real-time autonomous communication, continue to the Relay section below.

---

## LAN Relay (Real-Time Communication)

The relay system adds instant communication over your local network — no Git round-trip needed.

### Components

| File | Purpose |
|------|---------|
| `relay/server.py` | HTTP server — receives messages into a local inbox (port 9111) |
| `relay/bridge.py` | CLI client — send messages, ping, read inbox, get profiles |
| `relay/watcher.py` | Autonomous processor — feeds incoming prompts into `claude -p` and sends responses back |

### Setup

**1. Configure peer addresses**

Edit `relay/bridge.py` and fill in the `PEERS` dict with your devices' IPs or hostnames. Or set the `BRIDGE_PEER` environment variable:

```bash
export BRIDGE_PEER=http://192.168.0.100:9111  # the OTHER device's IP
```

**2. Start the relay server on both machines**

```bash
python relay/server.py
```

**3. Test connectivity**

```bash
python relay/bridge.py ping
```

**4. Send a message**

```bash
python relay/bridge.py send "Hello" "Testing the bridge"
python relay/bridge.py send-task "Deploy" "Please run make deploy"
python relay/bridge.py send-question "Status" "What are you working on?"
```

**5. Read messages**

```bash
python relay/bridge.py read
python relay/bridge.py ack <message_id>  # clear after reading
```

### Autonomous Mode (Watcher)

The watcher turns the bridge into a fully autonomous system — both Claude instances can prompt each other without you in the middle.

```bash
python relay/watcher.py              # Start watching
python relay/watcher.py --dry-run    # Preview without executing
python relay/watcher.py --interval 5 # Poll every 5 seconds
```

Send a prompt that the other device's watcher will auto-process:

```bash
python relay/bridge.py prompt "What Python version are you running?"
```

The watcher on the other device picks this up, runs `claude -p` with the prompt, and sends Claude's response back to your relay inbox.

### Making It Persistent

The relay and watcher should run as background services that survive reboots.

**macOS (launchd):**
```bash
bash scripts/setup-launchd.sh
```

**Windows (Scheduled Tasks) — run as Administrator:**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup-scheduled-task.ps1
```

These scripts create services that auto-start on login and auto-restart on crash.

---

## Connecting Your Devices

### Direct Ethernet (Simplest)

Plug an ethernet cable directly between two machines. They'll auto-assign link-local addresses (`169.254.x.x`) and discover each other via mDNS.

```bash
# Find the other machine
ping my-other-pc.local
# Or check the ARP table
arp -a
```

Add network info to your device profiles:
```yaml
network:
  ethernet:
    ip: 169.254.x.x
    link: "Direct cable to other-device.local"
    peer_ip: 169.254.x.x
```

### Same Wi-Fi / LAN

Both machines can reach each other by IP or hostname. Just configure the `PEERS` dict in `bridge.py` or set `BRIDGE_PEER`.

### Remote / Different Networks

The Git-based message protocol works across any network. The relay is LAN-only, but Git messages go through GitHub.

### Using with Claude Desktop (Cowork + Dispatch)

If you have the [Claude Desktop app](https://claude.ai/download), you can use **Cowork** (background agent mode) with **Dispatch** (remote task sending):

- Your always-on machine runs Claude Desktop in Cowork mode
- You send tasks remotely via Dispatch from your phone or another device
- Cowork reads the bridge repo to understand which machine to route work to
- Combined with the relay, Cowork can trigger work on either machine

Add the bridge location to your `~/.claude/CLAUDE.md` so Cowork knows about it automatically.

---

## Device Profiles

Each device gets a YAML file in `devices/`. The key sections:

```yaml
name: my-desktop
os: Windows 11
last_seen: "2026-03-19"
status: online

hardware:
  ram: 64 GB
  gpu: NVIDIA RTX 3070 (8GB VRAM)

tools:
  - name: ArcGIS Pro
  - name: Docker

strengths:
  - "GPU-accelerated ML"
  - "GIS workflows"

weaknesses:
  - "No iOS development"

network:
  ethernet:
    ip: 169.254.x.x
    link: "Direct cable to mac.local"
```

**strengths** and **weaknesses** are what Claude uses to decide where a task should run.

---

## Git Message Protocol

For durable, version-controlled communication:

**Filename:** `YYYY-MM-DD_HHMMSS_<from>_to_<to>.md`

```markdown
---
from: mac
to: windows
priority: normal
status: pending
type: task-request
---

## Deploy the updated API

The frontend changes are done. Please run `make deploy-staging`.
```

| Type | When to use |
|------|-------------|
| `task-request` | Asking the other device to do something |
| `info` | Letting the other device know what you did |
| `question` | Asking about the other device's state |
| `response` | Replying to a previous message |

Status flow: `pending` → `acknowledged` → `completed`

---

## Troubleshooting

### "claude CLI not found in PATH"

The watcher runs as a background process and may not inherit your shell's PATH. The watcher auto-detects common install locations, but if it fails:

```bash
# Find where claude is installed
which claude          # macOS/Linux
where claude          # Windows
Get-Command claude    # PowerShell
```

Set the PATH in your launch agent / scheduled task, or set `CLAUDE_BIN` in the watcher environment.

### Claude reads CLAUDE.md and gets confused

**Symptom:** Watcher responses say things like "Let me check messages" or try to use tools instead of responding.

**Cause:** `claude -p` was running from the bridge repo directory, picking up the bridge's CLAUDE.md instructions.

**Fix:** Already handled — the watcher runs Claude from a temp directory. If you still see this, check that you're on the latest watcher.py.

### Prompts arrive empty on Windows

**Symptom:** Claude responds "your message came through empty."

**Cause:** Passing the prompt as a CLI argument (`claude -p "..."`) has shell escaping issues on Windows.

**Fix:** Already handled — the watcher pipes the prompt via stdin instead of CLI arguments. Make sure you're on the latest watcher.py.

### Quick verification test

After setup, run this to confirm everything works end-to-end:

```bash
# On Device A — send a test prompt to Device B
python relay/bridge.py prompt "Reply with: BRIDGE WORKING from [your device name]"

# Wait ~15 seconds, then check for the response
python relay/bridge.py read
```

If you get a response back, the autonomous loop is working.

### Security note

The relay server uses plain HTTP with no authentication. It is designed for **trusted local networks** (direct ethernet, home LAN). Do not expose port 9111 to the public internet without adding authentication and TLS.

### When to use what

| Channel | Best for | Speed | Durability |
|---------|----------|-------|------------|
| **Git messages** | Task delegation, status updates, audit trail | Slow (push/pull) | Permanent |
| **LAN relay** | Quick questions, pinging, real-time chat | Instant | Until ack'd |
| **Watcher prompts** | Autonomous cross-device Claude work | ~10-30s | Until processed |

---

## File Structure

```
claude-bridge/
├── CLAUDE.md                    # Protocol instructions (auto-read by Claude Code)
├── .gitignore                   # Excludes relay runtime files
├── devices/
│   ├── example.yml              # Example device profile
│   └── (your devices here)
├── messages/
│   ├── archive/                 # Completed/old messages
│   └── (active messages here)
├── relay/
│   ├── server.py                # HTTP relay server (port 9111)
│   ├── bridge.py                # CLI client for sending/reading messages
│   └── watcher.py               # Autonomous prompt processor
├── scripts/
│   ├── setup-launchd.sh         # macOS persistence setup
│   └── setup-scheduled-task.ps1 # Windows persistence setup
└── README.md
```

---

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) running on 2+ machines
- [GitHub CLI](https://cli.github.com/) (`gh`) authenticated on each machine
- Python 3.8+ (for the relay — no pip packages needed, stdlib only)
- Git

---

## License

MIT — do whatever you want with it.
