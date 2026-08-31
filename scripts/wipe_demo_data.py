"""Reset the demo world: the agent's records go, the configuration stays.

Deletes every document in the collections the agent writes as it works — tasks, actions,
events, decisions, wiki_pages, and the _contract test scratch — and leaves `projects` (the
Acme configuration) and `evals` (published results the README cites) untouched. Optionally
archives a range of Linear issues so the board matches.

Dry-run by default; nothing is deleted without --apply.

    uv run --env-file .env python scripts/wipe_demo_data.py
    uv run --env-file .env python scripts/wipe_demo_data.py --apply --archive-linear 20:36
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import urllib.request

WIPE = ("tasks", "actions", "events", "decisions", "wiki_pages")
KEEP = ("projects", "evals")
TEAM = "1da250b0-0262-4438-847b-980e9249f989"


async def wipe_firestore(apply: bool) -> None:
    from google.cloud import firestore

    client = firestore.AsyncClient(project=os.environ["PM_GCP_PROJECT"])
    async for coll in client.collections():
        name = coll.id
        docs = [d async for d in coll.stream()]
        if name in KEEP:
            print(f"  keep   {name:<18} {len(docs)}")
            continue
        if name not in WIPE and not name.startswith("_contract"):
            print(f"  skip   {name:<18} {len(docs)} (unknown collection — not touching it)")
            continue
        if apply:
            for doc in docs:
                await doc.reference.delete()
            print(f"  wiped  {name:<18} {len(docs)}")
        else:
            print(f"  would wipe {name:<14} {len(docs)}")


def linear(query: str, variables: dict | None = None) -> dict:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        "https://api.linear.app/graphql", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": os.environ["PM_LINEAR_API_KEY"]},
    )
    return json.load(urllib.request.urlopen(req))


def archive_linear(span: str, apply: bool) -> None:
    low, high = (int(x) for x in span.split(":"))
    data = linear(
        'query($t: ID!) { issues(filter: {team: {id: {eq: $t}}}, first: 100) '
        '{ nodes { id identifier number archivedAt } } }', {"t": TEAM})
    targets = [n for n in data["data"]["issues"]["nodes"]
               if low <= n["number"] <= high and not n["archivedAt"]]
    for issue in sorted(targets, key=lambda n: n["number"]):
        if apply:
            linear('mutation($id: String!) { issueArchive(id: $id) { success } }',
                   {"id": issue["id"]})
            print(f"  archived {issue['identifier']}")
        else:
            print(f"  would archive {issue['identifier']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--archive-linear", metavar="LOW:HIGH", default="")
    args = parser.parse_args()

    print("Firestore:" + ("" if args.apply else " (dry run)"))
    asyncio.run(wipe_firestore(args.apply))
    if args.archive_linear:
        print("Linear:" + ("" if args.apply else " (dry run)"))
        archive_linear(args.archive_linear, args.apply)
    if not args.apply:
        print("\nnothing changed — re-run with --apply")


if __name__ == "__main__":
    main()
