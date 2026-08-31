"""Feature flags. Flipped per environment at deploy time."""

FLAGS = {
    "auto_reminders": True,        # send reminders without a human clicking
    "invoice_export_csv": False,   # CSV export of invoices (in development)
    "late_fees": False,            # charge late fees (not decided)
    "sms_reminders": False,        # never shipped
}


def enabled(name: str) -> bool:
    return FLAGS.get(name, False)
