from dataclasses import dataclass, field
from datetime import date


@dataclass
class Customer:
    id: str
    name: str
    email: str


@dataclass
class Invoice:
    id: str
    customer_id: str
    amount_cents: int
    issued_on: date
    due_on: date
    paid_on: date | None = None
    reminders_sent: list[date] = field(default_factory=list)

    @property
    def is_paid(self) -> bool:
        return self.paid_on is not None
