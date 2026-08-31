"""Runtime configuration. Environment overrides win over defaults."""

import os

# Days after an invoice's due date before the first payment reminder is sent.
REMINDER_DAYS = int(os.environ.get("ACME_REMINDER_DAYS", "7"))

# Days between subsequent reminders.
REMINDER_REPEAT_DAYS = int(os.environ.get("ACME_REMINDER_REPEAT_DAYS", "7"))

LATE_FEE_PERCENT = float(os.environ.get("ACME_LATE_FEE_PERCENT", "0"))
