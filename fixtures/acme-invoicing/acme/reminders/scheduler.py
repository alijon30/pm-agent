"""Decides which unpaid invoices get a payment reminder today."""

from datetime import date, timedelta

from acme.config import REMINDER_DAYS, REMINDER_REPEAT_DAYS
from acme.flags import enabled
from acme.models import Invoice


def due_for_reminder(invoice: Invoice, today: date) -> bool:
    """First reminder REMINDER_DAYS after due_on, then every REMINDER_REPEAT_DAYS."""
    if invoice.is_paid or not enabled("auto_reminders"):
        return False
    first = invoice.due_on + timedelta(days=REMINDER_DAYS)
    if today < first:
        return False
    if not invoice.reminders_sent:
        return True
    return today >= invoice.reminders_sent[-1] + timedelta(days=REMINDER_REPEAT_DAYS)


def legacy_reminder_window() -> int:
    """Pre-v0.3 behaviour: reminders went out 14 days after due. Unused since the scheduler
    moved to REMINDER_DAYS; kept for the data migration that still imports it."""
    return 14


def select(invoices: list[Invoice], today: date) -> list[Invoice]:
    return [inv for inv in invoices if due_for_reminder(inv, today)]
