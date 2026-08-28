"""Seed the Acme Invoicing Linear team with a believable backlog.

The texture matters more than the count: a stale dashboard request the Q3 call re-raises (the
planted near-duplicate), a closed experiment about reminder cadence (the closed twin), and
enough mundane work around them that finding either takes a real search rather than luck.

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
    ("Overdue invoices dashboard for finance",
     "Finance asked for a view of everything past due. Raised last quarter, never scheduled.",
     "Backlog", 4, False),  # ← the near-duplicate the Q3 call re-raises
    ("Reminder cadence experiment",
     "Tried a 5-day first reminder for two weeks in June. Reverted; inconclusive.",
     "Done", None, False),  # ← the closed twin near the reminder work
    ("Invoice PDF footer shows the wrong support email",
     "support@acme-invoicing.test moved to help@; the template still has the old one.",
     "Todo", 3, False),
    ("Customers table pagination breaks past 200 rows",
     "Offset pagination double-counts when invoices are created mid-scroll.",
     "In Progress", 2, False),
    ("Add currency column to payments export",
     "Two customers bill in EUR; the export assumes USD.",
     "Backlog", 3, False),
    ("Stripe webhook retries are not idempotent",
     "A retried payment.succeeded can mark an invoice paid twice.",
     "Todo", 2, False),
    ("Late-fee policy needs a decision",
     "Finance keeps asking. Product has not decided whether we charge at all.",
     "Backlog", 4, False),
    ("Empty state for the invoices list",
     "New accounts see a blank table with no call to action.",
     "Todo", 4, False),
    ("Reminder email copy sounds robotic",
     "Support hears complaints; wants a friendlier first reminder.",
     "Backlog", 4, False),
    ("Upgrade to Python 3.12 in CI",
     "Runners still on 3.11; dataclass slots patch wanted.",
     "Done", None, False),
    ("Invoice numbering skips on rollback",
     "A failed create burns a sequence number; auditors notice gaps.",
     "Todo", 3, False),
    ("Onboarding: import customers from CSV",
     "Biggest ask from sales for Q3.",
     "In Progress", 2, True),
    ("Payment reconciliation report",
     "Match Stripe payouts to invoices for the accountant.",
     "Backlog", 3, True),
    ("Rate-limit the public invoice status endpoint",
     "One customer polls it every second.",
     "Todo", 3, False),
    ("Dark mode for the customer portal",
     "Requested twice. Low priority.",
     "Backlog", 4, False),
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
