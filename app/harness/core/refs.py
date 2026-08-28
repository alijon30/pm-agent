"""A typed reference, as a person reads it.

`linear:INV-26` is the shape a gate checks and the shape an agent writes; it is not the shape
anyone should have to read. This turns one into the other, and lives in core because Slack, the
console, the graph and the report all show citations and must all shorten them identically."""

from __future__ import annotations

import re

REF = re.compile(r"^([a-z]+):(.+)$", re.IGNORECASE)


def ref_chip(ref: str) -> str:
    """`linear:INV-26` becomes "INV-26", a Fathom moment becomes "call @ 1:58", a decision id
    becomes "ledger". Anything whose kind we do not know comes back untouched — a reference we
    cannot shorten is still true."""
    match = REF.match((ref or "").strip())
    if not match:
        return (ref or "").strip()
    kind, target = match.group(1).lower(), match.group(2).strip()
    if kind == "linear":
        return target
    if kind == "decision":
        return "ledger"
    if kind == "notion":
        return "spec"
    if kind == "wiki":
        return "brain"
    if kind == "fathom":
        _meeting, _, timestamp = target.partition("@")
        stamp = timestamp.removeprefix("00:") if timestamp.startswith("00:") else timestamp
        return f"call @ {stamp}" if stamp else "call"
    if kind == "code":
        path, _, line = target.rpartition(":")
        if path and line.isdigit():
            return f"{path.rsplit('/', 1)[-1]}:{line}"
        return target.rsplit("/", 1)[-1]
    return (ref or "").strip()


def ref_chips(refs: list[str] | tuple[str, ...]) -> list[str]:
    """Readable citations, in order, without repeats — three decisions cited on one claim are
    one "ledger", not three."""
    chips: list[str] = []
    for ref in refs or []:
        chip = ref_chip(str(ref))
        if chip and chip not in chips:
            chips.append(chip)
    return chips
