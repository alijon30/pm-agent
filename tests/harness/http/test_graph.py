"""The graph is what a judge looks at, so it has to be both true and self-contained: every node
comes from a document the agent really wrote, and the page asks the network for nothing."""

from app.harness.deps import Deps
from app.harness.http.console import graph_data
from app.harness.store.actions import ActionStore
from app.harness.store.lessons import LessonStore
from fastapi.testclient import TestClient

from tests.conftest import ACME

PROJECT = {**ACME, "name": "Q3 Billing", "slack_channel_id": "C-product"}


async def a_whole_story(deps: Deps) -> dict[str, str]:
    """One call, one decision, one issue, one owner, one check, one lesson — the chain the
    graph exists to show. Returns the ids so a test can name what it expects."""
    await deps.projects.upsert("acme", PROJECT)
    deps.actions = ActionStore(deps.db, deps.clock)
    deps.lessons = LessonStore(deps.db, deps.clock)

    event_id = await deps.events.record(
        provider="fathom", provider_event_id="m1", project_id="acme",
        payload={"title": "Q3 Billing planning",
                 "transcript": [{"text": "the unredacted words of a call"}]})
    assert event_id is not None
    decision_ids = await deps.decisions.add_many(
        "acme", event_id,
        [{"statement": "Payment reminders move to three days after the due date.",
          "evidence": [{"quote": "let's move payment reminders", "timestamp": "00:01:42"}]}],
        {"meeting_id": "8841201", "title": "Q3 Billing planning", "url": ""})

    act_id = await deps.queue.enqueue(kind="act", project_id="acme", payload={}, reason="file",
                                      root_event_id=event_id)
    assert act_id is not None
    action_id = await deps.actions.begin(
        task_id=act_id, project_id="acme", kind="linear.create_issue", idempotency_key="k-1",
        inputs={"title": "Move payment reminders to three days", "owner": "Nodir Rahimov"})
    await deps.actions.finish(
        action_id, target_ids={"identifier": "INV-26", "url": "https://linear.app/a/INV-26"},
        revert={})

    first = await deps.queue.enqueue(
        kind="check_issue_state", project_id="acme", payload={},
        params={"issue": "INV-26", "expect": ["In Progress"]}, reason="is it underway?")
    assert first is not None
    second = await deps.queue.enqueue(
        kind="check_pr_exists", project_id="acme", payload={}, params={"issue": "INV-26"},
        reason="is there a PR?", depends_on=[first])
    assert second is not None
    await deps.db.update("tasks", first, {"status": "done",
                                          "result": {"met": True, "early": True}})

    lesson_id = await deps.lessons.add(
        project_id="acme", text="Give a pull request a full working day.",
        evidence=[f"task:{first}"], source_task_id="review-1")

    return {"event": event_id, "decision": decision_ids[0], "check": first,
            "dependent": second, "lesson": lesson_id}


# --- the data ------------------------------------------------------------------------------------

async def test_the_graph_is_built_from_what_the_agent_actually_did(deps: Deps) -> None:
    ids = await a_whole_story(deps)
    project = await deps.projects.get("acme")
    assert project is not None

    graph = await graph_data(project, deps)
    by_id = {n["id"]: n for n in graph["nodes"]}

    assert by_id[f"meeting:{ids['event']}"]["type"] == "meeting"
    assert by_id[f"meeting:{ids['event']}"]["label"] == "Q3 Billing planning"
    assert by_id[f"decision:{ids['decision']}"]["label"].startswith("Payment reminders move")
    assert by_id["issue:INV-26"]["url"] == "https://linear.app/a/INV-26"
    assert by_id["person:Nodir Rahimov"]["type"] == "person"
    assert by_id[f"task:{ids['check']}"]["label"] == "check that INV-26 is underway"
    assert by_id[f"lesson:{ids['lesson']}"]["type"] == "lesson"


async def test_a_check_carries_what_the_page_needs_to_colour_it(deps: Deps) -> None:
    ids = await a_whole_story(deps)
    project = await deps.projects.get("acme")
    assert project is not None

    by_id = {n["id"]: n for n in (await graph_data(project, deps))["nodes"]}

    assert by_id[f"task:{ids['check']}"]["status"] == "done"
    assert by_id[f"task:{ids['check']}"]["early"] is True
    assert by_id[f"task:{ids['dependent']}"]["status"] == "blocked"
    assert by_id[f"task:{ids['dependent']}"]["early"] is False


async def test_every_documented_relationship_is_drawn(deps: Deps) -> None:
    ids = await a_whole_story(deps)
    project = await deps.projects.get("acme")
    assert project is not None

    graph = await graph_data(project, deps)
    drawn = {(e["source"], e["target"], e["rel"]) for e in graph["edges"]}

    assert (f"meeting:{ids['event']}", f"decision:{ids['decision']}", "decided") in drawn
    assert (f"decision:{ids['decision']}", "issue:INV-26", "led to") in drawn
    assert ("issue:INV-26", "person:Nodir Rahimov", "owned by") in drawn
    assert (f"task:{ids['check']}", "issue:INV-26", "watches") in drawn
    assert (f"task:{ids['dependent']}", f"task:{ids['check']}", "waits on") in drawn
    assert (f"lesson:{ids['lesson']}", f"task:{ids['check']}", "learned from") in drawn


async def test_an_edge_to_something_that_is_not_on_the_graph_is_not_drawn(deps: Deps) -> None:
    """A lesson citing a task the cap dropped, and a check watching an issue nobody filed."""
    await deps.projects.upsert("acme", PROJECT)
    deps.lessons = LessonStore(deps.db, deps.clock)
    await deps.lessons.add(project_id="acme", text="from nowhere", evidence=["task:vanished"])
    await deps.queue.enqueue(kind="check_pr_exists", project_id="acme", payload={},
                             params={"issue": "INV-999"}, reason="watch a phantom")
    project = await deps.projects.get("acme")
    assert project is not None

    graph = await graph_data(project, deps)

    assert graph["edges"] == []
    assert "issue:INV-999" not in {n["id"] for n in graph["nodes"]}


async def test_a_decision_is_never_linked_to_an_issue_from_another_call(deps: Deps) -> None:
    ids = await a_whole_story(deps)
    other = await deps.events.record(provider="fathom", provider_event_id="m2",
                                     project_id="acme", payload={"title": "Another call"})
    assert other is not None
    stray = await deps.queue.enqueue(kind="act", project_id="acme", payload={}, reason="file",
                                     root_event_id=other)
    assert stray is not None and deps.actions is not None
    action_id = await deps.actions.begin(
        task_id=stray, project_id="acme", kind="linear.create_issue", idempotency_key="k-2",
        inputs={"title": "Unrelated work"})
    await deps.actions.finish(action_id, target_ids={"identifier": "INV-99"}, revert={})
    project = await deps.projects.get("acme")
    assert project is not None

    drawn = {(e["source"], e["target"]) for e in (await graph_data(project, deps))["edges"]}

    assert (f"decision:{ids['decision']}", "issue:INV-26") in drawn
    assert (f"decision:{ids['decision']}", "issue:INV-99") not in drawn


async def test_the_graph_stays_small_enough_to_read_but_keeps_the_people(deps: Deps) -> None:
    from app.harness.http.console import GRAPH_NODES

    await deps.projects.upsert("acme", PROJECT)
    for n in range(GRAPH_NODES + 40):
        await deps.queue.enqueue(kind="check_pr_exists", project_id="acme", payload={},
                                 params={"issue": f"INV-{n}"}, reason="watch")
    project = await deps.projects.get("acme")
    assert project is not None

    nodes = (await graph_data(project, deps))["nodes"]

    assert len(nodes) == GRAPH_NODES
    assert len([n for n in nodes if n["type"] == "person"]) == len(ACME["roster"])


async def test_a_secret_shaped_label_is_redacted_like_everywhere_else(deps: Deps) -> None:
    await deps.projects.upsert("acme", PROJECT)
    await deps.queue.enqueue(kind="check_moon_phase", project_id="acme", payload={},
                             reason="rejected by lin_api_SUPERSECRET during planning")
    project = await deps.projects.get("acme")
    assert project is not None

    labels = " ".join(n["label"] for n in (await graph_data(project, deps))["nodes"])

    assert "lin_api_SUPERSECRET" not in labels


async def test_the_graph_never_leaks_a_transcript(deps: Deps) -> None:
    await a_whole_story(deps)
    project = await deps.projects.get("acme")
    assert project is not None

    dumped = str(await graph_data(project, deps))

    assert "the unredacted words of a call" not in dumped


async def test_an_empty_database_is_an_empty_graph(client: TestClient, deps: Deps) -> None:
    async def nothing(slug: str) -> None:
        return None

    deps.projects.get = nothing  # type: ignore[method-assign]
    body = client.get("/console/graph.json").json()

    assert body["nodes"] == [] and body["edges"] == []
    assert body["generated_at"]


async def test_the_graph_json_route_serves_the_default_project(
    client: TestClient, deps: Deps
) -> None:
    await a_whole_story(deps)
    body = client.get("/console/graph.json").json()

    assert body["project"] == "Q3 Billing"
    assert {n["type"] for n in body["nodes"]} == {
        "meeting", "decision", "issue", "person", "check", "lesson"}


# --- the page ------------------------------------------------------------------------------------

def test_the_graph_page_serves(client: TestClient) -> None:
    response = client.get("/console/graph")

    assert response.status_code == 200
    assert "the agent's world, as it learned it" in response.text


def test_the_page_asks_the_network_for_nothing(client: TestClient) -> None:
    """It is served from a locked-down Cloud Run service and opened by someone who has no reason
    to trust us; every byte it needs is in the document."""
    page = client.get("/console/graph").text

    assert "src=\"http" not in page and "src='http" not in page
    assert "href=\"http" not in page and "href='http" not in page
    assert "@import" not in page and "cdn" not in page.lower()
    # The one absolute URL is the SVG namespace, which is an identifier and not a request.
    assert page.count("http") == page.count("http://www.w3.org/2000/svg")


def test_the_page_carries_the_replay_controls_the_demo_depends_on(client: TestClient) -> None:
    page = client.get("/console/graph").text

    for element_id in ("canvas", "edges", "nodes", "scrubber", "play", "clock", "count"):
        assert f"id='{element_id}'" in page or f'id="{element_id}"' in page
    assert "▶ Replay" in page
    assert "/console/graph.json" in page


def test_the_console_and_the_graph_link_to_each_other(client: TestClient) -> None:
    assert "/console/graph" in client.get("/console").text
    assert "href='/console'" in client.get("/console/graph").text


def test_every_node_type_the_builder_emits_has_a_colour_and_a_legend_entry() -> None:
    from app.harness.http.console import graph_page
    from app.harness.http.graph_assets import GRAPH_SCRIPT

    page = graph_page("x")
    for kind in ("meeting", "decision", "issue", "person", "check", "lesson"):
        assert f"{kind}:" in GRAPH_SCRIPT, f"no colour for {kind}"
    for label in ("call", "decision", "issue", "person", "check", "lesson"):
        assert f">{label}</span>" in page


def test_the_tuning_constants_are_declared_once_and_marked_as_taste() -> None:
    """They were chosen because the result reads well, not because they are derived from
    anything, and the next person to touch them should know that before they start."""
    from pathlib import Path

    from app.harness.http import graph_assets

    source = Path(str(graph_assets.__file__)).read_text()
    assert "taste, not truth" in source
    assert graph_assets.GRAPH_SCRIPT.count("const SIM = {") == 1


async def test_the_nodes_arrive_in_the_order_the_story_happened(deps: Deps) -> None:
    """The replay walks the array, so the array is the script. Everything a call produces shares
    a timestamp to the second, and within that second the order has to be causal or the graph
    shows an issue before the decision that caused it."""
    await a_whole_story(deps)
    project = await deps.projects.get("acme")
    assert project is not None

    kinds = [n["type"] for n in (await graph_data(project, deps))["nodes"]]
    first_of = {kind: kinds.index(kind) for kind in set(kinds)}

    assert first_of["meeting"] < first_of["decision"] < first_of["issue"]
    assert first_of["issue"] < first_of["check"] < first_of["lesson"]
    # The cast is on stage before the play starts: people have no timestamp of their own.
    assert first_of["person"] < first_of["meeting"]
