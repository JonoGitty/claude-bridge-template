# Claude Bridge

A shared repo for communication between Claude Code instances running on different devices. Both instances should pull before reading and push after writing.

## How It Works

1. **Device profiles** (`devices/`) — each device has a YAML file declaring what it can do
2. **Messages** (`messages/`) — timestamped markdown files for cross-device communication
3. **Git sync** — always `git pull` before reading, `git add + commit + push` after writing

## Device Profiles

Each device registers itself in `devices/<device-name>.yml`. These profiles declare:
- OS and hardware
- Available tools and software
- What kinds of tasks it's best at
- Current status (online/offline, last seen)

**Before routing a task, read all device profiles to decide where it should run.**

## Message Protocol

When Claude on one device needs to communicate with the other:

1. Create a file in `messages/` named: `YYYY-MM-DD_HHMMSS_<from>_to_<to>.md`
2. Use this format:

```markdown
---
from: device-a | device-b
to: device-a | device-b
priority: low | normal | high
status: pending | acknowledged | completed
type: task-request | info | question | response
---

## Subject line here

Body of the message.
```

3. Commit and push immediately
4. The receiving instance checks for pending messages on startup or when asked

When responding to a message, update its `status` to `acknowledged` or `completed` and add a response section at the bottom, then create a response message if needed.

## Routing Rules

When the user gives you a task, consider:
- Is this task better suited for the other device? (e.g., Mac-only software, Windows-only tools)
- Can I do it locally, or should I delegate?
- Should I inform the other instance about what I've done?

If delegating: create a task-request message, push, and tell the user to check the other device.
If informing: create an info message so the other instance stays aware.

## Checking In

When starting a conversation, if the user mentions cross-device work or you suspect relevance:
```bash
cd /path/to/claude-bridge && git pull
```
Then check `messages/` for any pending messages addressed to you.

## Archive

Move completed/old messages to `messages/archive/` periodically to keep the inbox clean.
