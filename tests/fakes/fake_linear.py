"""In-memory Linear. Same method surface and failure contract as LinearClient; writes are
recorded so tests can assert exactly what Act performed.

Issues are keyed by identifier (INV-142) rather than UUID: Linear accepts either in `issue(id:)`
and the harness only ever holds identifiers, so the fake stays honest about what we pass."""

from __future__ import annotations

import copy
from typing import Any

from app.harness.core.errors import SourceUnavailable


class FakeLinear:
    def __init__(
        self,
        issues: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
        members: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
        states: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    ) -> None:
        self._issues: dict[str, dict[str, Any]] = {
            i["identifier"]: copy.deepcopy(i) for i in issues
        }
        self._members = [copy.deepcopy(m) for m in members]
        self._states = [copy.deepcopy(s) for s in states]
        self.writes: list[dict[str, Any]] = []
        self._counter = max((int(i.split("-", 1)[1]) for i in self._issues), default=100)

    def _existing(self, issue_id: str) -> dict[str, Any]:
        issue = self._issues.get(issue_id)
        if issue is None:
            raise SourceUnavailable("linear", f"unknown issue {issue_id}")
        return issue

    async def get_issue(self, identifier: str) -> dict[str, Any] | None:
        issue = self._issues.get(identifier)
        return copy.deepcopy(issue) if issue is not None else None

    async def search_issues(
        self, team_id: str, text: str, *, limit: int = 8
    ) -> list[dict[str, Any]]:
        # The fixture company has one team, so team_id is accepted but not filtered on.
        needle = text.lower()
        hits = [
            copy.deepcopy(i)
            for i in self._issues.values()
            if needle in (i.get("title") or "").lower()
            or needle in (i.get("description") or "").lower()
        ]
        return hits[:limit]

    async def list_states(self, team_id: str) -> list[dict[str, Any]]:
        return [copy.deepcopy(s) for s in self._states]

    async def list_members(self, team_id: str) -> list[dict[str, Any]]:
        return [copy.deepcopy(m) for m in self._members]

    async def create_issue(
        self,
        *,
        team_id: str,
        project_id: str | None,
        title: str,
        description: str,
        assignee_id: str | None,
        priority: int | None,
        due_date: str | None,
    ) -> dict[str, Any]:
        self._counter += 1
        identifier = f"INV-{self._counter}"
        assignee = next((m for m in self._members if m["id"] == assignee_id), None)
        issue = {
            "id": f"uuid-{self._counter}",
            "identifier": identifier,
            "title": title,
            "description": description,
            "state": "Triage",
            "priority": priority,
            "assignee": {"id": assignee["id"], "name": assignee["name"]} if assignee else None,
            "due_date": due_date,
            "url": f"https://linear.app/acme/issue/{identifier}",
            "updated_at": "",
        }
        self._issues[identifier] = issue
        self.writes.append({
            "op": "create", "identifier": identifier, "team_id": team_id,
            "project_id": project_id, "title": title, "description": description,
            "assignee_id": assignee_id, "priority": priority, "due_date": due_date,
        })
        return {"id": issue["id"], "identifier": identifier, "url": issue["url"]}

    async def update_issue(self, issue_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        issue = self._existing(issue_id)
        issue.update(copy.deepcopy(fields))
        self.writes.append({"op": "update", "identifier": issue_id, "fields": dict(fields)})
        return {"id": issue["id"], "identifier": issue_id}

    async def comment(self, issue_id: str, body: str) -> str:
        self._existing(issue_id)
        comment_id = f"comment-{len(self.writes) + 1}"
        self.writes.append({"op": "comment", "identifier": issue_id, "body": body})
        return comment_id
