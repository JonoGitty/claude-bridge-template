# Claude Bridge

**A private communication bridge between Claude Code instances running on different machines.**

If you run [Claude Code](https://docs.anthropic.com/en/docs/claude-code) on multiple devices (e.g. a Windows desktop and a MacBook), they have no way to coordinate. Claude Bridge solves this with a dead-simple approach: a shared private Git repo that both instances can read and write to.

Each device registers a **capability profile** — what OS it runs, what tools are installed, what projects live there, and what it's best at. When you give either instance a task, it can check the other device's profile and decide whether to handle it locally, delegate it, or inform the other instance about what it did.

Communication happens through **timestamped message files** — no servers, no APIs, just Git.

---

## How It Works

```
┌─────────────────┐                              ┌─────────────────┐
│   Device A      │                              │   Device B      │
│   (e.g. Mac)    │                              │  (e.g. Windows) │
│                 │         ┌──────────┐         │                 │
│  Claude Code ◄──┼────────►│  GitHub   │◄───────┼──► Claude Code  │
│                 │  push/  │  (private │  push/ │                 │
│  devices/       │  pull   │   repo)   │  pull  │  devices/       │
│  messages/      │         └──────────┘        │  messages/      │
│  CLAUDE.md      │                              │  CLAUDE.md      │
└─────────────────┘                              └─────────────────┘
```

1. **Device profiles** (`devices/*.yml`) — each device declares its OS, tools, projects, and strengths
2. **Messages** (`messages/*.md`) — cross-device communication via timestamped markdown files
3. **CLAUDE.md** — protocol instructions that Claude Code reads automatically when working in the repo
4. **Git** — `pull` before reading, `commit + push` after writing. That's the entire sync mechanism.

---

## Quick Start

### 1. Create your private bridge repo

```bash
gh repo create my-claude-bridge --private --clone
cd my-claude-bridge
```

### 2. Copy the template files

Clone or download this template, then copy the contents into your private repo:

```bash
# Copy CLAUDE.md, devices/, messages/ into your private repo
cp -r claude-bridge-template/* my-claude-bridge/
```

Or just copy the files manually — there aren't many.

### 3. Set up Device A

On your first machine, clone your private repo and fill in the device profile:

```bash
cd /path/to/your/ai/folder
gh repo clone your-username/my-claude-bridge
cd my-claude-bridge
```

Edit `devices/device-a.yml` (rename it to something meaningful like `mac.yml` or `desktop.yml`) and fill in your device's capabilities. See [devices/example.yml](devices/example.yml) for the full format.

Then tell Claude Code about it. The simplest way: just work from inside the repo directory, and Claude will read the `CLAUDE.md` automatically. Or add the repo path to your Claude Code memory so it knows where to find it.

### 4. Set up Device B

Repeat on your second machine:

```bash
gh repo clone your-username/my-claude-bridge
cd my-claude-bridge
```

Create a new device profile (e.g. `devices/windows.yml`) with that machine's capabilities.

### 5. Done

Both Claude Code instances can now:
- Read each other's capability profiles
- Route tasks to the best device
- Leave messages for each other
- Stay aware of what the other has done

---

## Device Profiles

Each device gets a YAML file in `devices/`. Here's what to include:

```yaml
name: my-desktop
os: Windows 11
last_seen: "2026-03-19"
status: online

hardware:
  ram: 64 GB
  gpu: NVIDIA RTX 3070 (8GB VRAM)
  cuda: "11.8"

languages:
  - name: Python 3.10
  - name: Node.js v24
  - name: Rust 1.85

dev_tools:
  - name: Git
  - name: GitHub CLI
  - name: VS Code
  - name: Docker

# Software specific to this machine
tools:
  - name: ArcGIS Pro
    notes: "GIS analysis"
  - name: Playwright
    notes: "Browser automation"

projects:
  - name: My Web App
    path: "C:\\Projects\\webapp"
  - name: ML Pipeline
    path: "C:\\Projects\\ml-pipeline"

strengths:
  - "GPU-accelerated ML training and inference"
  - "GIS workflows"
  - "Windows-specific development"

weaknesses:
  - "No Docker"
  - "No iOS development"
```

The key sections are **strengths** and **weaknesses** — these are what Claude uses to decide where a task should run.

---

## Message Protocol

When one instance needs to communicate with the other, it creates a file in `messages/`:

**Filename:** `YYYY-MM-DD_HHMMSS_<from>_to_<to>.md`

**Format:**
```markdown
---
from: mac
to: windows
priority: normal
status: pending
type: task-request
---

## Deploy the updated API

The frontend changes are done on this machine. The Windows box has Docker
and the deployment keys — please run `make deploy-staging` in /Projects/api.
```

### Message types

| Type | When to use |
|------|-------------|
| `task-request` | Asking the other device to do something |
| `info` | Letting the other device know what you did |
| `question` | Asking about the other device's state or capabilities |
| `response` | Replying to a previous message |

### Status flow

`pending` → `acknowledged` → `completed`

The receiving instance updates the status and can add a response section at the bottom of the file.

Old messages get moved to `messages/archive/` to keep the inbox clean.

---

## Routing Logic

When you give Claude a task, it should consider:

1. **Can I do this locally?** Check my own device profile — do I have the right tools?
2. **Would the other device be better?** Check the other profile's strengths/weaknesses.
3. **Should I delegate or inform?**
   - **Delegate:** Create a `task-request` message, push, tell the user to check the other device
   - **Inform:** Create an `info` message so the other instance stays aware

The `CLAUDE.md` file contains the full protocol instructions that Claude Code reads automatically.

---

## Tips

- **Keep profiles up to date.** When you install new software or start new projects, update the YAML.
- **Check messages on startup.** Tell Claude to `git pull` and check for pending messages when you begin a session.
- **Archive regularly.** Move completed messages to `messages/archive/` so the inbox stays scannable.
- **More than 2 devices?** Works fine — just add more device profiles. Messages use `from`/`to` fields so routing stays clear.
- **Disk space, hardware info matters.** Including things like available disk space or GPU specs helps Claude make better routing decisions (e.g. "don't send ML training to the machine with 8GB RAM").

---

## File Structure

```
claude-bridge/
├── CLAUDE.md                          # Protocol instructions (auto-read by Claude Code)
├── devices/
│   ├── example.yml                    # Example device profile (copy and customize)
│   └── (your devices here)
├── messages/
│   ├── archive/                       # Completed/old messages
│   └── (active messages here)
└── README.md
```

---

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) running on 2+ machines
- [GitHub CLI](https://cli.github.com/) (`gh`) authenticated on each machine
- Git installed on each machine

---

## License

MIT — do whatever you want with it.
