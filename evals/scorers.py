"""Scorers: pure functions from (question, run) to a pass or a fail with the reason.

A question is one of three kinds, and the distinction matters when reading the numbers:

- **recall** — did the model find a moment we planted in the fixture call? This is the part that
  can genuinely regress when a prompt or a model changes.
- **guarantee** — did a deterministic gate hold across everything the run produced? These are
  meant to pass every time; a guarantee that fails is a bug in the harness, not in the model,
  and is the most valuable failure this suite can report.
- **gate** — a gate probed directly with input the pipeline would never produce on its own (a
  plan naming an issue that does not exist, a plan with a cycle).

Every scorer takes the whole run, so a question can look at any stage's output. The run bundle
is documented in run_evals.execute(); the keys used here are:

    extract · reconcile · act · plan · report · decisions · actions · scheduled · issues
    seeded_identifiers · policy · roster · transcript · meeting_id · gate · errors
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.harness.core.clock import parse_iso
from app.harness.verify.evidence import normalize, quote_in_transcript
from app.harness.verify.priority import has_escalation


@dataclass(frozen=True)
class Score:
    passed: bool
    detail: str


Scorer = Callable[[dict[str, Any], dict[str, Any]], Score]


def _ok(detail: str) -> Score:
    return Score(True, detail)


def _no(detail: str) -> Score:
    return Score(False, detail)


def _matches(text: str, expected: dict[str, Any]) -> bool:
    """`contains` must all appear; `any_of` needs one. Both are normalised, so "three days"
    matches "Three  Days" and a model's punctuation never decides a question."""
    haystack = normalize(text)
    if any(normalize(w) not in haystack for w in expected.get("contains") or []):
        return False
    alternatives = expected.get("any_of") or []
    return not alternatives or any(normalize(w) in haystack for w in alternatives)


def _created(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Every issue the agent filed, as the action log recorded the intent."""
    return [
        a for a in run.get("actions") or []
        if a.get("kind") == "linear.create_issue" and a.get("status") == "done"
    ]


def _items(run: dict[str, Any]) -> list[dict[str, Any]]:
    return list((run.get("reconcile") or {}).get("items") or [])


def _item_for(run: dict[str, Any], title_contains: str) -> dict[str, Any] | None:
    needle = normalize(title_contains)
    for item in _items(run):
        if needle in normalize(str(item.get("title") or "")):
            return item
    return None


def _all_conflicts(run: dict[str, Any]) -> list[dict[str, Any]]:
    reconcile = run.get("reconcile") or {}
    return [c for item in _items(run) for c in item.get("conflicts") or []] + list(
        reconcile.get("decision_conflicts") or []
    )


def _claims(run: dict[str, Any]) -> list[dict[str, Any]]:
    report = (run.get("report") or {}).get("report") or {}
    return [c for section in report.get("sections") or [] for c in section.get("claims") or []]


# --- identifiers ------------------------------------------------------------------------------


def identifier_pattern(known: set[str]) -> re.Pattern[str] | None:
    """A regex for this tracker's issue keys only (INV-142, not UTF-8). Built from the keys the
    tracker actually holds, so a scan can never invent a false positive out of ordinary prose."""
    prefixes = sorted({k.split("-", 1)[0] for k in known if "-" in k})
    if not prefixes:
        return None
    return re.compile(rf"\b(?:{'|'.join(prefixes)})-\d+\b")


def written_identifiers(run: dict[str, Any]) -> list[str]:
    """Every issue key the agent wrote anywhere a human or another system will read it: issue
    bodies, citations, conflict sources, report references, scheduled check params, and the
    targets of its own actions."""
    known = {str(i.get("identifier")) for i in run.get("issues") or []}
    pattern = identifier_pattern(known)
    if pattern is None:
        return []

    prose: list[str] = [str(i.get("description") or "") for i in run.get("issues") or []]
    for item in _items(run):
        prose.extend(str(c) for c in item.get("citations") or [])
        prose.extend(str(f.get("source") or "") for f in item.get("facts") or [])
    for conflict in _all_conflicts(run):
        prose.extend(str(s.get("source") or "") for s in conflict.get("sides") or [])
    for claim in _claims(run):
        prose.extend(str(r) for r in claim.get("refs") or [])

    found: list[str] = [m for text in prose for m in pattern.findall(text)]
    for action in run.get("actions") or []:
        for value in ((action.get("target_ids") or {}).get("identifier"),
                      (action.get("inputs") or {}).get("target_issue")):
            if value:
                found.append(str(value))
    for task in run.get("scheduled") or []:
        issue = (task.get("params") or {}).get("issue")
        if issue:
            found.append(str(issue))
    return found


def fabricated_identifiers(run: dict[str, Any]) -> list[str]:
    """Issue keys the agent wrote that the tracker has never heard of. This is the number that
    decides whether any of the rest is worth reading."""
    known = {str(i.get("identifier")) for i in run.get("issues") or []}
    seen: list[str] = []
    for identifier in written_identifiers(run):
        if identifier not in known and identifier not in seen:
            seen.append(identifier)
    return seen


# --- recall: the planted moments --------------------------------------------------------------


def decision_recorded(row: dict[str, Any], run: dict[str, Any]) -> Score:
    """A decision from the call reached the ledger."""
    for decision in run.get("decisions") or []:
        if _matches(str(decision.get("statement") or ""), row["expected"]):
            return _ok(str(decision["statement"])[:90])
    return _no(f"{len(run.get('decisions') or [])} decision(s), none matching")


def rejected_option_recorded(row: dict[str, Any], run: dict[str, Any]) -> Score:
    """An alternative the call considered and turned down was kept with the decision."""
    for decision in run.get("decisions") or []:
        text = " ".join(str(o) for o in decision.get("rejected_options") or [])
        if text and _matches(text, row["expected"]):
            return _ok(f"{decision.get('statement', '')[:50]} — rejected: {text[:40]}")
    return _no("no decision carries this rejected option")


def action_item_extracted(row: dict[str, Any], run: dict[str, Any]) -> Score:
    for item in (run.get("extract") or {}).get("action_items") or []:
        if _matches(f"{item.get('title', '')} {item.get('description', '')}", row["expected"]):
            return _ok(str(item.get("title"))[:90])
    return _no("no action item matches")


def open_question_extracted(row: dict[str, Any], run: dict[str, Any]) -> Score:
    for question in (run.get("extract") or {}).get("open_questions") or []:
        if _matches(str(question.get("question") or ""), row["expected"]):
            return _ok(str(question.get("question"))[:90])
    return _no(f"{len((run.get('extract') or {}).get('open_questions') or [])} open question(s)")


def due_hint_captured(row: dict[str, Any], run: dict[str, Any]) -> Score:
    """The timing words as spoken — the thing the date gate needs before it will set a date."""
    for item in (run.get("extract") or {}).get("action_items") or []:
        if item.get("due_hint") and _matches(str(item["due_hint"]), row["expected"]):
            return _ok(f"{item.get('title', '')[:50]} — due_hint {item['due_hint']!r}")
    return _no("no action item carries the spoken timing")


def escalation_quote_captured(row: dict[str, Any], run: dict[str, Any]) -> Score:
    """The escalation language is only usable if it was captured verbatim; without it the
    priority gate clamps, however urgent the model believes the work is."""
    item = _item_for(run, str(row["expected"].get("title_contains") or ""))
    if item is None:
        return _no("no reconciled item with that title")
    quotes = [str(q) for q in item.get("quotes") or []]
    phrases = [str(p) for p in row["expected"].get("phrases") or []]
    if has_escalation(quotes, phrases):
        return _ok(f"quoted: {'; '.join(quotes)[:80]}")
    return _no(f"{len(quotes)} quote(s), none containing {phrases}")


def owner_assigned(row: dict[str, Any], run: dict[str, Any]) -> Score:
    needle = normalize(str(row["expected"].get("title_contains") or ""))
    wanted = str(row["expected"].get("owner") or "")
    for action in _created(run):
        inputs = action.get("inputs") or {}
        if needle in normalize(str(inputs.get("title") or "")):
            owner = inputs.get("owner")
            if owner == wanted:
                return _ok(f"{action.get('target_ids', {}).get('identifier')} → {owner}")
            return _no(f"assigned to {owner!r}, expected {wanted!r}")
    return _no("nothing was filed with that title")


def duplicate_detected(row: dict[str, Any], run: dict[str, Any]) -> Score:
    """The call re-raised work that already had a ticket, and the agent pointed at it instead of
    opening a second one."""
    needle = normalize(str(row["expected"].get("title_contains") or ""))
    targets = [
        str(i.get("identifier")) for i in run.get("issues") or []
        if str(i.get("identifier")) in (run.get("seeded_identifiers") or [])
        and needle in normalize(str(i.get("title") or ""))
    ]
    if not targets:
        return _no("the fixture tracker has no seeded issue with that title")
    for item in _items(run):
        if item.get("disposition") in ("duplicate_of", "update") and str(
            item.get("target_issue") or ""
        ) in targets:
            return _ok(f"{item['disposition']} {item['target_issue']}")
    dispositions = [f"{i.get('disposition')}→{i.get('target_issue')}" for i in _items(run)]
    return _no(f"expected one of {targets}; got {dispositions}")


def conflict_detected(row: dict[str, Any], run: dict[str, Any]) -> Score:
    kinds = [str(k) for k in row["expected"].get("kinds") or []]
    for conflict in _all_conflicts(run):
        if kinds and str(conflict.get("kind")) not in kinds:
            continue
        if _matches(str(conflict.get("about") or ""), row["expected"]):
            return _ok(f"{conflict.get('kind')}: {conflict.get('about')}")
    return _no(f"{len(_all_conflicts(run))} conflict(s), none matching")


# --- guarantees: the gates, across everything this run produced --------------------------------


def evidence_verbatim(row: dict[str, Any], run: dict[str, Any]) -> Score:
    """Every quote that survived the evidence gate really is in the transcript."""
    plain = normalize(str(run.get("transcript") or ""))
    extract = run.get("extract") or {}
    checked, bad = 0, []
    for item in list(extract.get("action_items") or []) + list(extract.get("open_questions") or []):
        for evidence in item.get("evidence") or []:
            checked += 1
            if not quote_in_transcript(str(evidence.get("quote") or ""), plain):
                bad.append(str(evidence.get("quote"))[:50])
    if checked == 0:
        return _no("nothing was extracted, so nothing was verified")
    return _ok(f"{checked} quote(s) verbatim") if not bad else _no(f"not in transcript: {bad}")


def decision_ledger_cited(row: dict[str, Any], run: dict[str, Any]) -> Score:
    decisions = run.get("decisions") or []
    if not decisions:
        return _no("the ledger is empty")
    uncited = [d for d in decisions if not str(d.get("source") or "").startswith("fathom:")]
    return _ok(f"{len(decisions)} entries, all sourced") if not uncited else _no(
        f"{len(uncited)} entry(ies) with no call reference"
    )


def roster_miss_unassigned(row: dict[str, Any], run: dict[str, Any]) -> Score:
    """Someone not on this project was named in the call. Nothing may be assigned to them."""
    roster = {normalize(n) for n in run.get("roster") or []}
    wrong = [
        str((a.get("inputs") or {}).get("owner"))
        for a in _created(run)
        if (a.get("inputs") or {}).get("owner")
        and normalize(str((a.get("inputs") or {}).get("owner"))) not in roster
    ]
    return _ok(f"{len(_created(run))} filed, none off-roster") if not wrong else _no(
        f"assigned to non-members: {wrong}"
    )


def priority_band_respected(row: dict[str, Any], run: dict[str, Any]) -> Score:
    """Nothing left the project's priority band without someone having said it was urgent."""
    band = (run.get("policy") or {}).get("priority_band") or [2, 4]
    phrases = (run.get("policy") or {}).get("escalation_phrases") or []
    violations: list[str] = []
    for action in _created(run):
        priority = (action.get("inputs") or {}).get("priority")
        if priority is None or int(band[0]) <= int(priority) <= int(band[1]):
            continue
        item = _item_for(run, str((action.get("inputs") or {}).get("title") or ""))
        quotes = [str(q) for q in (item or {}).get("quotes") or []]
        if not (int(priority) < int(band[0]) and has_escalation(quotes, phrases)):
            violations.append(f"{action.get('target_ids', {}).get('identifier')}=P{priority}")
    return _ok(f"{len(_created(run))} filed, band {band} held") if not violations else _no(
        f"outside the band with nothing said: {violations}"
    )


def due_only_when_stated(row: dict[str, Any], run: dict[str, Any]) -> Score:
    """A due date is a commitment: it may only exist where the words that made it were spoken."""
    plain = normalize(str(run.get("transcript") or ""))
    unspoken: list[str] = []
    dated = 0
    for action in _created(run):
        inputs = action.get("inputs") or {}
        if not inputs.get("due"):
            continue
        dated += 1
        item = _item_for(run, str(inputs.get("title") or ""))
        hint = normalize(str((item or {}).get("due_hint") or ""))
        if not hint or hint not in plain:
            unspoken.append(f"{action.get('target_ids', {}).get('identifier')}={inputs['due']}")
    return _ok(f"{dated} dated issue(s), each spoken aloud") if not unspoken else _no(
        f"dates nobody said: {unspoken}"
    )


def issue_cites_the_call(row: dict[str, Any], run: dict[str, Any]) -> Score:
    """Every filed issue can be audited from Linear alone, without opening this system."""
    filed = {str((a.get("target_ids") or {}).get("identifier")) for a in _created(run)}
    bodies = {
        str(i.get("identifier")): str(i.get("description") or "")
        for i in run.get("issues") or []
    }
    if not filed:
        return _no("nothing was filed")
    missing = [i for i in sorted(filed) if "From the call" not in bodies.get(i, "")]
    return _ok(f"{len(filed)} issue(s) quote the call") if not missing else _no(
        f"no call reference in: {missing}"
    )


def conflict_not_resolved(row: dict[str, Any], run: dict[str, Any]) -> Score:
    """Where two sources disagree the agent reports both with citations; it never picks."""
    conflicts = _all_conflicts(run)
    if not conflicts:
        return _no("no conflicts were found in a call that contains two")
    thin = [
        str(c.get("about"))
        for c in conflicts
        if len(c.get("sides") or []) < 2
        or any(not s.get("source") for s in c.get("sides") or [])
    ]
    return _ok(f"{len(conflicts)} conflict(s), both sides cited") if not thin else _no(
        f"one-sided or uncited: {thin}"
    )


def plan_dependency_order(row: dict[str, Any], run: dict[str, Any]) -> Score:
    """A check that only makes sense after another waits for it, and is due no earlier."""
    scheduled = {str(t["id"]): t for t in run.get("scheduled") or []}
    if not scheduled:
        return _no("the plan materialised nothing")
    edges, bad = 0, []
    for task in scheduled.values():
        for dep_id in task.get("depends_on") or []:
            dependency = scheduled.get(str(dep_id))
            if dependency is None:
                continue
            edges += 1
            if str(dependency.get("due_at") or "") > str(task.get("due_at") or ""):
                bad.append(f"{task['kind']} due before {dependency['kind']}")
    if edges == 0:
        return _no(f"{len(scheduled)} scheduled check(s) but no dependency between any of them")
    return _ok(f"{edges} edge(s), each due in order") if not bad else _no(str(bad))


def plan_within_horizon(row: dict[str, Any], run: dict[str, Any]) -> Score:
    horizon = int((run.get("policy") or {}).get("plan_horizon_days", 30))
    now = parse_iso(str(run["now"]))
    scheduled = run.get("scheduled") or []
    if not scheduled:
        return _no("the plan materialised nothing")
    bad = [
        f"{t['kind']}@{t.get('due_at')}"
        for t in scheduled
        if not 0 <= (parse_iso(str(t["due_at"])) - now).days <= horizon
    ]
    return _ok(f"{len(scheduled)} check(s) inside {horizon} days") if not bad else _no(str(bad))


# --- gates, probed directly -------------------------------------------------------------------


def plan_rejects_unknown_issue(row: dict[str, Any], run: dict[str, Any]) -> Score:
    verdict = (run.get("gate") or {}).get("unknown_issue") or {}
    reasons = " ".join(r.get("reason", "") for r in verdict.get("rejected") or [])
    if verdict.get("tasks"):
        return _no("a plan naming an issue that does not exist was accepted")
    return _ok(reasons[:90] or "rejected")


def plan_rejects_cycle(row: dict[str, Any], run: dict[str, Any]) -> Score:
    verdict = (run.get("gate") or {}).get("cycle") or {}
    if verdict.get("tasks"):
        return _no("a plan containing a dependency cycle was partially accepted")
    return _ok("; ".join(verdict.get("reasons") or [])[:90] or "rejected")


# --- the report -------------------------------------------------------------------------------


def report_citation_coverage(row: dict[str, Any], run: dict[str, Any]) -> Score:
    claims = _claims(run)
    if not claims:
        return _no("the report contains no claims")
    uncited = [str(c.get("text"))[:40] for c in claims if not (c.get("refs") or [])]
    removed = len((run.get("report") or {}).get("removed") or [])
    return _ok(
        f"{len(claims)}/{len(claims)} claims cited ({removed} removed by the gate)"
    ) if not uncited else _no(f"uncited claims survived: {uncited}")


def report_refs_exist(row: dict[str, Any], run: dict[str, Any]) -> Score:
    """Every tracker and ledger reference in the delivered report points at something real."""
    known_issues = {str(i.get("identifier")) for i in run.get("issues") or []}
    known_decisions = {str(d.get("id")) for d in run.get("decisions") or []}
    meeting = str(run.get("meeting_id") or "")
    bad: list[str] = []
    checked = 0
    for claim in _claims(run):
        for ref in claim.get("refs") or []:
            kind, _, target = str(ref).partition(":")
            if kind == "linear":
                checked += 1
                if target not in known_issues:
                    bad.append(str(ref))
            elif kind == "decision":
                checked += 1
                if target not in known_decisions:
                    bad.append(str(ref))
            elif kind == "fathom":
                checked += 1
                if target.partition("@")[0] != meeting:
                    bad.append(str(ref))
    if checked == 0:
        return _no("the report cites nothing this scorer can re-check")
    return _ok(f"{checked} reference(s) resolve") if not bad else _no(f"dangling: {bad}")


def no_fabricated_identifiers(row: dict[str, Any], run: dict[str, Any]) -> Score:
    """The single number that decides whether the rest of the report is worth reading."""
    fabricated = fabricated_identifiers(run)
    total = len(written_identifiers(run))
    return _ok(f"{total} identifier(s) written, all real") if not fabricated else _no(
        f"invented: {fabricated}"
    )


SCORERS: dict[str, Scorer] = {
    "decision_recorded": decision_recorded,
    "rejected_option_recorded": rejected_option_recorded,
    "action_item_extracted": action_item_extracted,
    "open_question_extracted": open_question_extracted,
    "due_hint_captured": due_hint_captured,
    "escalation_quote_captured": escalation_quote_captured,
    "owner_assigned": owner_assigned,
    "duplicate_detected": duplicate_detected,
    "conflict_detected": conflict_detected,
    "evidence_verbatim": evidence_verbatim,
    "decision_ledger_cited": decision_ledger_cited,
    "roster_miss_unassigned": roster_miss_unassigned,
    "priority_band_respected": priority_band_respected,
    "due_only_when_stated": due_only_when_stated,
    "issue_cites_the_call": issue_cites_the_call,
    "conflict_not_resolved": conflict_not_resolved,
    "plan_dependency_order": plan_dependency_order,
    "plan_within_horizon": plan_within_horizon,
    "plan_rejects_unknown_issue": plan_rejects_unknown_issue,
    "plan_rejects_cycle": plan_rejects_cycle,
    "report_citation_coverage": report_citation_coverage,
    "report_refs_exist": report_refs_exist,
    "no_fabricated_identifiers": no_fabricated_identifiers,
}
