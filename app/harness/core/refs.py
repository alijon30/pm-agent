"""A typed reference, as a person reads it."""

from __future__ import annotations

import re

REF = re.compile(r"^([a-z]+):(.+)$", re.IGNORECASE)


def ref_chip(ref: str) -> str:
    """`linear:INV-26` becomes "INV-26", a Fathom moment becomes "call @ 1:58", a decision id
    becomes "decided on the call". Anything whose kind we do not know comes back untouched."""
    match = REF.match((ref or "").strip())
    if not match:
        return (ref or "").strip()
    kind, target = match.group(1).lower(), match.group(2).strip()
    if kind == "linear":
        return target
    if kind == "decision":
        return "decided on the call"
    if kind == "notion":
        return "the spec"
    if kind == "wiki":
        return "brain"
    if kind == "fathom":
        _meeting, _, timestamp = target.partition("@")
        stamp = timestamp.removeprefix("00:") if timestamp.startswith("00:") else timestamp
        if stamp and ":" not in stamp:
            stamp = f"0:{stamp}"  # "00:22" is twenty-two seconds in, not minute twenty-two
        return f"call @ {stamp}" if stamp else "call"
    if kind == "code":
        path, _, line = target.rpartition(":")
        if path and line.isdigit():
            return f"{path.rsplit('/', 1)[-1]}:{line}"
        return target.rsplit("/", 1)[-1]
    return (ref or "").strip()


def ref_chips(refs: list[str] | tuple[str, ...]) -> list[str]:
    """Readable citations, in order, without repeats."""
    chips: list[str] = []
    for ref in refs or []:
        chip = ref_chip(str(ref))
        if chip and chip not in chips:
            chips.append(chip)
    return chips
