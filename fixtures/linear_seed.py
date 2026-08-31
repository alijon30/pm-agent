"""Seed the InterviewPrepPro Linear team with a believable backlog.

The texture matters more than the count: a pricing-page request the planning call re-raises
(the planted near-duplicate), a closed experiment as the closed twin, and enough mundane work
around them that finding either takes a real search rather than luck.

Idempotent: an issue whose exact title already exists is skipped, so re-running repairs a
partial seed instead of duplicating it.

Run:  uv run --env-file .env python fixtures/linear_seed.py
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
from typing import Any

import httpx

API = "https://api.linear.app/graphql"
TEAM_ID = "1da250b0-0262-4438-847b-980e9249f989"
PROJECT_ID = "5d09ebb7-0e9b-45ff-848e-d704778478ea"

# (title, description, state name, priority or None, in_project)
SEED: list[tuple[str, str, str, int | None, bool]] = [
    ("Build the pricing page",
     "The upgrade section shows Free / Pro / Institution, but there is no public /pricing "
     "route. Raised before launch, never scheduled.",
     "Backlog", 3, True),
    ("Question set search and filtering",
     "Students want to filter the nine visa categories and search sample questions.",
     "Backlog", 3, True),
    ("Wire notification preferences to real emails",
     "Settings collects notification toggles; nothing sends email yet.",
     "Backlog", 4, False),
    ("Community feed moderation tools",
     "Member stories need a report button and an admin hide action before we scale invites.",
     "Backlog", 4, False),
    ("Spike: multilingual interviewer voices",
     "Explored offering the mock interview in Uzbek and Hindi. Parked after the vendor quoted "
     "per-language costs; revisit when Institution tier lands.",
     "Done", None, False),
]


async def gql(client: httpx.AsyncClient, key: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    resp = await client.post(API, json={"query": query, "variables": variables},
                             headers={"Authorization": key})
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    if data.get("errors"):
        raise RuntimeError(str(data["errors"])[:300])
    return data["data"]


async def main() -> None:
    key = os.environ["PM_LINEAR_API_KEY"]
    async with httpx.AsyncClient(timeout=30) as client:
        states = await gql(client, key, """
            query($teamId: String!) { team(id: $teamId) { states { nodes { id name } } } }
        """, {"teamId": TEAM_ID})
        state_ids = {n["name"]: n["id"] for n in states["team"]["states"]["nodes"]}

        existing = await gql(client, key, """
            query($teamId: ID) {
              issues(first: 100, filter: { team: { id: { eq: $teamId } } }) { nodes { title } }
            }
        """, {"teamId": TEAM_ID})
        have = {n["title"] for n in existing["issues"]["nodes"]}

        created = 0
        for title, description, state, priority, in_project in SEED:
            if title in have:
                continue
            if state not in state_ids:
                raise SystemExit(f"team has no state named {state!r}; has {sorted(state_ids)}")
            issue_input: dict[str, Any] = {
                "teamId": TEAM_ID, "title": title, "description": description,
                "stateId": state_ids[state],
            }
            if priority is not None:
                issue_input["priority"] = priority
            if in_project:
                issue_input["projectId"] = PROJECT_ID
            result = await gql(client, key, """
                mutation($input: IssueCreateInput!) {
                  issueCreate(input: $input) { success issue { identifier } }
                }
            """, {"input": issue_input})
            print("created", result["issueCreate"]["issue"]["identifier"], "—", title)
            created += 1
        print(f"done: {created} created, {len(have)} already present")

        ids = {"linear_team_id": TEAM_ID, "linear_project_id": PROJECT_ID}
        acme = pathlib.Path(__file__).parent / "projects" / "acme.json"
        doc = json.loads(acme.read_text())
        doc.update(ids)
        acme.write_text(json.dumps(doc, indent=2) + "\n")
        print("fixtures/projects/acme.json updated:", ids)


if __name__ == "__main__":
    asyncio.run(main())
