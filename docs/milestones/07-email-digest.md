# Milestone 7: Email Digest Delivery

**Status:** Planned
**Dependencies:** Milestone 2 (Social Proof Signals), Milestone 3 (Citation Velocity)

## Overview

Automated email delivery of digest-worthy papers. Only papers meeting the HIGH BAR (breakthrough score >= 0.8 OR aggregate score >= 0.7) will be included.

## Goals

1. Daily email digest with breakthrough papers
2. Configurable delivery schedule
3. Beautiful HTML email templates
4. Unsubscribe and preference management

## Features

### Email Template

```
Subject: ArXiv Digest: {count} Breakthrough Papers Found

------------------------------------------
BREAKTHROUGH ALERT
------------------------------------------

1. [0.92] Paper Title Here
   ArXiv: 2312.12345

   Key Insight: One sentence summary...

   Why it matters: Claude's assessment of significance...

   [Read More] [Save for Later]

------------------------------------------

2. [0.85] Another Paper
   ...

------------------------------------------
DIGEST SUMMARY
------------------------------------------

- Papers scanned: 150
- Breakthrough papers: 3
- Assessment confidence: High

Adjust your preferences: [Settings Link]
Unsubscribe: [Unsubscribe Link]
```

### Configuration

```python
# .env additions
EMAIL_ENABLED=true
EMAIL_PROVIDER=sendgrid  # or ses, smtp
EMAIL_FROM=digest@yourdomain.com
EMAIL_TO=you@email.com
DIGEST_SCHEDULE=daily  # or weekly
DIGEST_TIME=08:00  # Local time
DIGEST_TIMEZONE=America/New_York
```

### CLI Commands

```bash
# Send digest now (for testing)
python main.py --send-digest

# Preview digest (don't send)
python main.py --preview-digest

# Schedule digest
python main.py --schedule-digest --time 08:00
```

## Implementation Plan

### Phase 1: Email Infrastructure
- [ ] Add email provider abstraction (SendGrid, SES, SMTP)
- [ ] Create HTML email template engine
- [ ] Add email configuration to settings

### Phase 2: Digest Generation
- [ ] Create DigestGenerator class
- [ ] Format papers for email display
- [ ] Add paper action links (read, save, dismiss)

### Phase 3: Scheduling
- [ ] Add scheduler (APScheduler or similar)
- [ ] Configurable delivery times
- [ ] Timezone support

### Phase 4: Preferences
- [ ] Email preference storage
- [ ] Unsubscribe handling
- [ ] Frequency controls

## Technical Notes

### Email Providers

**SendGrid (Recommended for MVP):**
- Free tier: 100 emails/day
- Simple API
- Good deliverability

**AWS SES:**
- Cheap at scale
- Requires domain verification
- More setup required

**SMTP:**
- Works with any provider
- Manual configuration
- Good for self-hosted

### Security Considerations

- Store email credentials in environment variables
- Use secure unsubscribe tokens
- Rate limit email sending
- Log email delivery status

## Future Enhancements

- Multiple recipient support
- Digest sharing
- Paper discussion threads
- Mobile-optimized templates
- Push notifications as alternative
