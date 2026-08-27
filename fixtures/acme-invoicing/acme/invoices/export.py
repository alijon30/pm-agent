"""Invoice export. CSV is behind the invoice_export_csv flag and currently omits payments."""

import csv
import io

from acme.flags import enabled
from acme.models import Invoice

COLUMNS = ["id", "customer_id", "amount_cents", "issued_on", "due_on"]


def to_csv(invoices: list[Invoice]) -> str:
    if not enabled("invoice_export_csv"):
        raise PermissionError("invoice_export_csv is disabled")
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(COLUMNS)
    for inv in invoices:
        writer.writerow([inv.id, inv.customer_id, inv.amount_cents, inv.issued_on, inv.due_on])
    return buf.getvalue()
