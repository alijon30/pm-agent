"""Block Kit builders. Pure functions: dicts in, dicts out, no I/O — so the exact shape of what
the team sees is unit-testable, and the summary can never fail the run that produced it.

Slack rejects a message with more than 50 blocks, so every builder truncates and says so rather
than losing the whole post."""

from __future__ import annotations

from typing import Any

MAX_BLOCKS = 50
REVERT_ACTION = "revert"
WRONG_ACTION = "wrong"


def _section(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _context(text: str) -> dict[str, Any]:
    return {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}


def revert_button(action_id: str, label: str = "Revert") -> dict[str, Any]:
    return {
        "type": "button",
        "text": {"type": "plain_text", "text": label},
        "action_id": f"{REVERT_ACTION}:{action_id}",
        "value": action_id,
        "style": "danger",
    }


def wrong_button(post_ref: str, label: str = "Something's wrong") -> dict[str, Any]:
    return {
        "type": "button",
        "text": {"type": "plain_text", "text": label},
        "action_id": f"{WRONG_ACTION}:{post_ref}",
        "value": post_ref,
    }


def _truncate(blocks: list[dict[str, Any]], keep_last: int = 1) -> list[dict[str, Any]]:
    """Trim the middle, not the end: the action buttons must survive."""
    if len(blocks) <= MAX_BLOCKS:
        return blocks
    head = blocks[: MAX_BLOCKS - keep_last - 1]
    tail = blocks[-keep_last:] if keep_last else []
    dropped = len(blocks) - len(head) - len(tail)
    return [*head, _context(f"_… {dropped} more not shown; see the console_"), *tail]


def call_summary_blocks(
    meeting: dict[str, Any],
    created: list[dict[str, Any]],
    updated: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    *,
    post_ref: str = "",
) -> list[dict[str, Any]]:
    """One message per call: what was filed, what was skipped, what disagrees, and a revert
    button per action performed."""
    title = meeting.get("title") or "call"
    url = meeting.get("url") or ""
    heading = f"*<{url}|{title}>*" if url else f"*{title}*"
    blocks: list[dict[str, Any]] = [
        _section(f"{heading}\n{len(created)} filed · {len(updated)} updated · "
                 f"{len(skipped)} skipped · {len(conflicts)} conflict(s)")
    ]

    for item in created:
        owner = item.get("owner") or "_unassigned_"
        line = f"• *<{item.get('url', '')}|{item.get('identifier', '?')}>* {item.get('title', '')}"
        blocks.append(_section(f"{line}\nowner: {owner}"))
        if item.get("note"):
            blocks.append(_context(item["note"]))

    for item in updated:
        blocks.append(
            _section(f"• *<{item.get('url', '')}|{item.get('identifier', '?')}>* "
                     f"{item.get('note') or 'updated'}")
        )

    for item in skipped:
        blocks.append(_context(f"skipped — {item.get('title', '?')}: {item.get('reason', '')}"))

    for conflict in conflicts:
        sides = "\n".join(
            f"    · {s.get('claim', '')}  _{s.get('source', '')}_"
            for s in conflict.get("sides", [])
        )
        blocks.append(_section(f"⚠️ *sources disagree* — {conflict.get('about', '')}\n{sides}"))

    elements = [revert_button(a["id"], f"Revert {a.get('label', 'action')}") for a in actions]
    if post_ref:
        elements.append(wrong_button(post_ref))
    if elements:
        blocks.append({"type": "actions", "elements": elements[:5]})
    return _truncate(blocks)


def plan_summary_blocks(tasks: list[dict[str, Any]], trimmed: list[str]) -> list[dict[str, Any]]:
    """The agent saying what it will check, and when — the visible half of the planner."""
    if not tasks:
        return [_section("_No follow-ups scheduled._")]
    lines = [
        f"• `{t.get('kind', '?')}` — {t.get('reason', '')} _(due {t.get('due_at', '')[:10]})_"
        for t in tasks
    ]
    blocks = [_section(f"*Planned {len(tasks)} follow-up(s)*\n" + "\n".join(lines))]
    if trimmed:
        blocks.append(_context(f"_{len(trimmed)} proposed task(s) rejected: {'; '.join(trimmed)}_"))
    return _truncate(blocks)


def wrong_modal(post_ref: str) -> dict[str, Any]:
    """The correction form. Its callback_id carries the post it is about."""
    return {
        "type": "modal",
        "callback_id": "correction",
        "private_metadata": post_ref,
        "title": {"type": "plain_text", "text": "Correct the agent"},
        "submit": {"type": "plain_text", "text": "Save"},
        "blocks": [
            {
                "type": "input",
                "block_id": "wrong",
                "label": {"type": "plain_text", "text": "What did it get wrong?"},
                "element": {"type": "plain_text_input", "action_id": "value", "multiline": True},
            },
            {
                "type": "input",
                "block_id": "right",
                "label": {"type": "plain_text", "text": "What should it do instead?"},
                "element": {"type": "plain_text_input", "action_id": "value", "multiline": True},
            },
            {
                "type": "input",
                "block_id": "scope",
                "label": {"type": "plain_text", "text": "Applies to"},
                "element": {
                    "type": "static_select",
                    "action_id": "value",
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "This project"},
                        "value": "project",
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "This project"},
                         "value": "project"},
                        {"text": {"type": "plain_text", "text": "Everywhere"}, "value": "global"},
                    ],
                },
            },
        ],
    }
