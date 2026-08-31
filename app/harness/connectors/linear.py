"""Linear over GraphQL."""

from __future__ import annotations

from typing import Any

import httpx

from app.harness.core.errors import SourceUnavailable
from app.harness.core.redact import redact

_ISSUE_FIELDS = """
id identifier title description url priority updatedAt dueDate
state { name type } assignee { id name }
"""

_GET_ISSUE = f"query($id: String!) {{ issue(id: $id) {{ {_ISSUE_FIELDS} }} }}"

_SEARCH = f"""
query($filter: IssueFilter, $first: Int!) {{
  issues(first: $first, filter: $filter) {{ nodes {{ {_ISSUE_FIELDS} }} }}
}}
"""


def search_filter(team_id: str, text: str) -> dict[str, Any]:
    """Every word must appear somewhere in the title or description. containsIgnoreCase wants a
    contiguous substring, so "overdue dashboard" as one phrase misses "Overdue invoices
    dashboard" — per-word AND is what a human means by that search."""
    words = [w for w in text.split() if w]
    return {
        "team": {"id": {"eq": team_id}},
        "and": [
            {"or": [{"title": {"containsIgnoreCase": w}},
                    {"description": {"containsIgnoreCase": w}}]}
            for w in words
        ],
    }

_STATES = """
query($teamId: String!) {
  team(id: $teamId) { states { nodes { id name type } } }
}
"""

_MEMBERS = """
query($teamId: String!) {
  team(id: $teamId) { members { nodes { id name email } } }
}
"""

_CREATE = """
mutation($input: IssueCreateInput!) {
  issueCreate(input: $input) { success issue { id identifier url } }
}
"""

_TEAM_LABELS = """
query($team: String!) {
  team(id: $team) { labels { nodes { id name } } }
}
"""

_LABEL_CREATE = """
mutation($input: IssueLabelCreateInput!) {
  issueLabelCreate(input: $input) { issueLabel { id name } }
}
"""

_UPDATE = """
mutation($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) { success issue { id identifier } }
}
"""

_ARCHIVE = """
mutation($id: String!) {
  issueArchive(id: $id) { success }
}
"""

_COMMENT = """
mutation($input: CommentCreateInput!) {
  commentCreate(input: $input) { success comment { id } }
}
"""


class _NotFound(Exception):
    """Internal: a GraphQL 'entity not found' answer. Never escapes this module."""


def _norm_issue(raw: dict[str, Any]) -> dict[str, Any]:
    assignee = raw.get("assignee")
    return {
        "id": raw["id"],
        "identifier": raw["identifier"],
        "title": raw.get("title") or "",
        "description": raw.get("description") or "",
        "state": (raw.get("state") or {}).get("name") or "",
        # Linear's own enum, not the display name — survives a team renaming its columns.
        "state_type": (raw.get("state") or {}).get("type") or "",
        "priority": raw.get("priority"),
        "assignee": {"id": assignee["id"], "name": assignee["name"]} if assignee else None,
        "due_date": raw.get("dueDate"),
        "url": raw.get("url") or "",
        "updated_at": raw.get("updatedAt") or "",
    }


class LinearClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.linear.app/graphql",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._headers = {"Authorization": api_key, "Content-Type": "application/json"}
        self._base_url = base_url
        self._transport = transport

    async def _gql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=20) as client:
                resp = await client.post(
                    self._base_url,
                    json={"query": query, "variables": variables},
                    headers=self._headers,
                )
        except httpx.HTTPError as exc:
            raise SourceUnavailable("linear", redact(str(exc))) from exc
        if resp.status_code >= 400:
            raise SourceUnavailable("linear", f"HTTP {resp.status_code}")
        data: dict[str, Any] = resp.json()
        errors = data.get("errors") or []
        if errors:
            message = "; ".join(str(e.get("message", "")) for e in errors)
            # "Entity not found" is an answer, not an outage; callers map it to None.
            if "not found" in message.lower():
                raise _NotFound(message)
            raise SourceUnavailable("linear", redact(message))
        return data.get("data") or {}

    async def get_issue(self, identifier: str) -> dict[str, Any] | None:
        try:
            data = await self._gql(_GET_ISSUE, {"id": identifier})
        except _NotFound:
            return None
        issue = data.get("issue")
        return _norm_issue(issue) if issue else None

    async def search_issues(
        self, team_id: str, text: str, *, limit: int = 8
    ) -> list[dict[str, Any]]:
        data = await self._gql(_SEARCH, {"filter": search_filter(team_id, text), "first": limit})
        nodes = (data.get("issues") or {}).get("nodes") or []
        return [_norm_issue(n) for n in nodes]

    async def list_states(self, team_id: str) -> list[dict[str, Any]]:
        data = await self._gql(_STATES, {"teamId": team_id})
        nodes = ((data.get("team") or {}).get("states") or {}).get("nodes") or []
        return [dict(n) for n in nodes]

    async def list_members(self, team_id: str) -> list[dict[str, Any]]:
        data = await self._gql(_MEMBERS, {"teamId": team_id})
        nodes = ((data.get("team") or {}).get("members") or {}).get("nodes") or []
        return [dict(n) for n in nodes]

    async def _label_ids(self, team_id: str, names: list[str]) -> list[str]:
        """Ids for the given label names on this team, creating any that do not exist yet."""
        data = await self._gql(_TEAM_LABELS, {"team": team_id})
        existing = {
            str(n["name"]).lower(): str(n["id"])
            for n in ((data.get("team") or {}).get("labels") or {}).get("nodes") or []
        }
        ids: list[str] = []
        for name in names:
            key = name.strip().lower()
            if not key:
                continue
            if key not in existing:
                made = await self._gql(
                    _LABEL_CREATE, {"input": {"name": key, "teamId": team_id}}
                )
                node = (made.get("issueLabelCreate") or {}).get("issueLabel") or {}
                if node.get("id"):
                    existing[key] = str(node["id"])
            if key in existing:
                ids.append(existing[key])
        return ids

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
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"teamId": team_id, "title": title, "description": description}
        if project_id:
            payload["projectId"] = project_id
        if assignee_id:
            payload["assigneeId"] = assignee_id
        if priority is not None:
            payload["priority"] = priority
        if due_date:
            payload["dueDate"] = due_date
        if labels:
            try:
                # A label is decoration on a ticket that must exist either way.
                payload["labelIds"] = await self._label_ids(team_id, labels)
            except SourceUnavailable:
                pass
        data = await self._gql(_CREATE, {"input": payload})
        issue = (data.get("issueCreate") or {}).get("issue") or {}
        return {
            "id": issue.get("id"),
            "identifier": issue.get("identifier"),
            "url": issue.get("url"),
        }

    async def archive_issue(self, identifier: str) -> None:
        """Archiving is its own Linear mutation and wants the UUID, not the key — an
        issueUpdate with an "archived" field is a 400, which is how the revert button spent a
        day silently doing nothing."""
        issue = await self.get_issue(identifier)
        if issue is None or not issue.get("id"):
            raise SourceUnavailable("linear", f"{identifier} not found")
        await self._gql(_ARCHIVE, {"id": str(issue["id"])})

    async def update_issue(self, issue_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        data = await self._gql(_UPDATE, {"id": issue_id, "input": fields})
        issue = (data.get("issueUpdate") or {}).get("issue") or {}
        return {"id": issue.get("id"), "identifier": issue.get("identifier")}

    async def comment(self, issue_id: str, body: str) -> str:
        data = await self._gql(_COMMENT, {"input": {"issueId": issue_id, "body": body}})
        return str(((data.get("commentCreate") or {}).get("comment") or {}).get("id") or "")
