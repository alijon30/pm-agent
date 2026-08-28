"""Write fixtures/projects/acme.json + fixtures/roster.json into Firestore as projects/acme.
Idempotent; re-run whenever the ids change. Requires ADC and PM_GCP_PROJECT."""

import asyncio
import json
from pathlib import Path

from app.config import Settings
from app.harness.store.firestore import FirestoreDb
from app.harness.store.projects import ProjectStore

ROOT = Path(__file__).parents[1] / "fixtures"


async def main() -> None:
    settings = Settings()
    project = json.loads((ROOT / "projects" / "acme.json").read_text())
    project["roster"] = json.loads((ROOT / "roster.json").read_text())
    db = FirestoreDb(settings.gcp_project, settings.firestore_database)
    await ProjectStore(db, settings.default_project_slug).upsert(project["slug"], project)
    sprint = project.get("sprint") or {}
    window = (
        f"{sprint.get('name')} ({sprint.get('start')} → {sprint.get('end')})"
        if sprint else "no sprint set — reports will cover the last 14 days"
    )
    print(f"seeded projects/{project['slug']} with {len(project['roster'])} roster members")
    print(f"  sprint: {window}")


if __name__ == "__main__":
    asyncio.run(main())
