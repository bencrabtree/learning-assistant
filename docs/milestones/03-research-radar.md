# Milestone 3: Research Radar Daemon

**Status:** In Progress (PR #14)
**Priority:** High - Core async functionality
**Dependencies:** Milestone 1 (Analysis Engine), Milestone 2 (Social Signals)

---

## Overview

Build a background daemon that continuously monitors for noteworthy papers and sends notifications when important discoveries are found.

**The Problem:**
- Users can't constantly poll for new papers
- Important papers might be missed if not checking regularly
- Need proactive notification when something noteworthy appears

**The Solution:**
- Background daemon running on schedule (e.g., every 3 hours, 5am-8pm)
- Scans both new papers AND rising/trending older papers
- Filters to noteworthy papers based on configurable thresholds
- Sends email notifications when papers meet criteria

---

## Key Features

### 1. Background Daemon
- Runs continuously in foreground (`--radar`)
- Single scan mode for testing (`--radar-once`)
- Configurable schedule (interval, start/end hours, timezone)
- Graceful shutdown via signals

### 2. Dual Discovery Mode
- **New Papers:** Last 1-2 days via full pipeline
- **Rising Papers:** Older papers gaining traction via HN signals

### 3. Noteworthy Filtering
A paper is noteworthy if ANY of:
- Breakthrough score > threshold (default: 60%)
- Social score > threshold AND relevance > threshold
- Very high relevance (> 80%)

### 4. Email Notifications
- HTML and plaintext formats
- Shows paper scores, authors, links
- Different subjects for breakthrough vs trending papers
- Gmail SMTP support with app passwords

---

## CLI Commands

```bash
# Test email configuration
python main.py --test-email

# Run a single radar scan
python main.py --radar-once

# Start the daemon (runs in foreground)
python main.py --radar
```

---

## Configuration

Environment variables in `.env`:

```bash
# Enable the radar
RADAR_ENABLED=true

# Schedule (default: every 3 hours, 5am-8pm EST)
RADAR_INTERVAL_HOURS=3
RADAR_START_HOUR=5
RADAR_END_HOUR=20
RADAR_TIMEZONE=America/New_York

# Notification thresholds
NOTIFY_BREAKTHROUGH_THRESHOLD=0.6
NOTIFY_SOCIAL_THRESHOLD=0.3
NOTIFY_RELEVANCE_THRESHOLD=0.5

# Email settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
RECIPIENT_EMAIL=your-email@gmail.com
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  ResearchRadar Daemon               │
├─────────────────────────────────────────────────────┤
│                                                     │
│   start() ──► while running:                        │
│                 │                                   │
│                 ├─► _is_within_schedule()?          │
│                 │     │                             │
│                 │     YES ──► _run_scan_cycle()     │
│                 │                 │                 │
│                 │                 ├─► discover_new  │
│                 │                 ├─► find_rising   │
│                 │                 ├─► filter_noteworthy
│                 │                 └─► notify        │
│                 │                                   │
│                 └─► sleep(interval)                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Files

- `src/radar/daemon.py` - Main daemon implementation
- `src/radar/__init__.py` - Module exports
- `src/services/email_notifier.py` - Email sending
- `src/config.py` - Radar configuration settings
- `tests/radar/test_daemon.py` - Daemon tests
- `tests/services/test_email_notifier.py` - Email tests

---

## What's Next

This milestone provides basic async functionality. **Milestone 4** will refactor this to be truly agentic using LangGraph:

- The radar loop becomes a LangGraph workflow
- Conditional edges decide whether to continue or notify
- State accumulates across iterations
- The graph itself decides when to stop

See `docs/milestones/04-agentic-langgraph.md` for details.

---

## Success Criteria

- [ ] Daemon runs on configurable schedule
- [ ] Discovers both new and rising papers
- [ ] Filters to noteworthy based on thresholds
- [ ] Sends email notifications
- [ ] Tests pass with 80%+ coverage
- [ ] Manual E2E test succeeds
