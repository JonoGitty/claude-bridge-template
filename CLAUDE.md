# Claude Bridge

A shared repo for communication between Claude Code instances running on different devices.

## Communication Channels

### Git Messages (durable)
- Always `git pull` before reading, `git add + commit + push` after writing
- Messages live in `messages/` as timestamped markdown files
- Format: `YYYY-MM-DD_HHMMSS_<from>_to_<to>.md` with YAML frontmatter

### LAN Relay (real-time)
If the relay server is running on both devices:
```bash
python relay/bridge.py ping                          # Check if other device is up
python relay/bridge.py send "subject" "body"         # Send a message
python relay/bridge.py send-task "subject" "body"    # Send a task request
python relay/bridge.py prompt "do something"         # Auto-processed by watcher
python relay/bridge.py read                          # Read your pending messages
python relay/bridge.py ack <id>                      # Clear a message
python relay/bridge.py profile                       # Get other device's profile
```

If the relay server isn't running, start it:
```bash
python relay/server.py
```

## Device Profiles

Each device registers itself in `devices/<device-name>.yml`. **Before routing a task, read all device profiles to decide where it should run.**

## Routing Rules

When the user gives you a task, consider:
- Is this task better suited for the other device? Check strengths/weaknesses in profiles.
- Can I do it locally, or should I delegate?
- Should I inform the other instance about what I've done?

If delegating: create a task-request message (via relay or git), and tell the user.
If informing: create an info message so the other instance stays aware.

## Checking In

When starting a conversation, if the user mentions cross-device work:
```bash
cd /path/to/claude-bridge && git pull
ls messages/*.md  # check for pending git messages
python relay/bridge.py read  # check relay inbox (if server running)
```

## Archive

Move completed/old messages to `messages/archive/` periodically.
