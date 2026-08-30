"""The graph is what a judge looks at, so it has to be both true and self-contained: every node
comes from a document the agent really wrote, and the page asks the network for nothing."""

import json
from datetime import timedelta

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
    assert "person:Nodir Rahimov" not in by_id, "people are badges and a strip, not nodes"
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


async def test_the_graph_stays_small_enough_to_read(deps: Deps) -> None:
    from app.harness.http.console import GRAPH_NODES

    await deps.projects.upsert("acme", PROJECT)
    for n in range(GRAPH_NODES + 40):
        await deps.queue.enqueue(kind="check_pr_exists", project_id="acme", payload={},
                                 params={"issue": f"INV-{n}"}, reason="watch")
    project = await deps.projects.get("acme")
    assert project is not None

    nodes = (await graph_data(project, deps))["nodes"]

    assert len(nodes) == GRAPH_NODES
    assert all(n["type"] != "person" for n in nodes)


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
        "meeting", "decision", "issue", "check", "lesson"}
    assert [r["first_name"] for r in body["roster"]] == ["Maya", "Nodir", "Priya", "Tom"]


# --- the page ------------------------------------------------------------------------------------

def test_the_graph_page_serves(client: TestClient) -> None:
    response = client.get("/console/graph")

    assert response.status_code == 200
    assert "Each column is a day · each row a kind of work" in response.text

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

    for element_id in ("top", "stage", "world", "canvas", "defs", "rules", "edges", "layer",
                       "gutter", "nowtag", "avatars", "now-btn", "status-dot", "status-text",
                       "scrubber", "play", "clock", "count", "mode", "tooltip"):
        assert f"id='{element_id}'" in page or f'id="{element_id}"' in page
    assert ">Replay<" in page
    assert "/console/graph.json" in page

def test_the_page_carries_the_frame_the_diagram_hangs_on(client: TestClient) -> None:
    """Position is the whole idea, so the pieces that make position readable — day columns,
    lane rows, the now line, the stage strip — are part of the page, not something to infer."""
    page = client.get("/console/graph").text

    for piece in (".col", ".col-head", ".col.future", ".lane", ".lane-tag", "#nowline",
                  "#nowtag", ".strip", ".seg", ".card", ".issue", ".text-chip"):
        assert piece in page, f"the page needs {piece}"
    assert "Scheduled" in page, "a future column says what it is"

def test_the_diagram_never_moves_on_its_own(client: TestClient) -> None:
    """The old page was a force simulation and a reviewer who looked twice saw two pictures.
    Every position now comes from the server, so there is nothing left to converge."""
    page = client.get("/console/graph").text

    assert "const SIM" not in page
    assert "function physics(" not in page
    assert "graph_layout.py" in page, "the page says where its positions are decided"


def test_the_surface_is_flat(client: TestClient) -> None:
    """The neon pass is gone: no filters, no gradients standing in for depth, no glow. What is
    left is a tracker — flat surfaces and one accent used sparingly."""
    from app.harness.http.graph_assets import GRAPH_SCRIPT, GRAPH_STYLE

    page = client.get("/console/graph").text

    for banned in ("<filter", "feGaussianBlur", "radialGradient", "linearGradient",
                   "backdrop-filter", "drop-shadow", "@keyframes beat", "@keyframes live",
                   "@keyframes pulse", "@keyframes rise"):
        assert banned not in GRAPH_STYLE, f"{banned} belongs to the old look"
        assert banned not in GRAPH_SCRIPT, f"{banned} belongs to the old look"
    assert "defineGlow" not in GRAPH_SCRIPT
    # An inset shadow is a rail, not depth; only a cast shadow would be the old look.
    cast = [line for line in page.splitlines()
            if "box-shadow" in line and "inset" not in line]
    assert len(cast) <= 1, f"one hairline shadow on the tooltip, no more: {cast}"


def test_the_page_draws_the_status_marks_it_needs(client: TestClient) -> None:
    """None of this comes from a library, and every state a check can be in has a mark."""
    from app.harness.http.graph_assets import GRAPH_SCRIPT

    page = client.get("/console/graph").text

    assert "function statusIcon(" in GRAPH_SCRIPT
    for kind in ("done", "early", "cancelled", "progress", "blocked", "backlog"):
        assert kind in GRAPH_SCRIPT, f"no status mark for {kind}"
    assert "function priorityBars(" in GRAPH_SCRIPT
    assert "id='arrow'" in page, "dependency arrows keep their head"

def test_a_label_reaches_the_page_as_text_and_never_as_markup(client: TestClient) -> None:
    """Labels are issue titles and model output. The server escapes them; this page must not
    undo that by building nodes out of concatenated strings."""
    page = client.get("/console/graph").text

    import re

    assert re.search(r"innerHTML\s*=", page) is None, "nothing is built by concatenating markup"
    assert "innerHTML" in page, "the rule is written down where the next person will read it"
    assert page.count("textContent") >= 3


def test_the_tuning_block_still_holds_every_constant_the_look_depends_on(
    client: TestClient,
) -> None:
    page = client.get("/console/graph").text

    for knob in ("head", "gutter", "laneMin", "laneEmpty", "rowGap", "minSlot", "issueSlot",
                 "cardSlot", "rowPitch", "chipPitch", "cardPitch", "stepMs", "edgeBow",
                 "tailColumns", "longEdgeColumns"):
        assert f"{knob}:" in page

def test_the_console_and_the_graph_link_to_each_other(client: TestClient) -> None:
    assert "/console/graph" in client.get("/console").text
    assert "href='/console'" in client.get("/console/graph").text


def test_every_check_state_the_builder_emits_has_a_mark_to_draw() -> None:
    """A state with no mark would render as a shape that means nothing."""
    from app.harness.http.graph_assets import GRAPH_SCRIPT
    from app.harness.http.graph_layout import SETTLED

    for state in (*SETTLED, "queued", "blocked", "leased"):
        assert f"{state}:" in GRAPH_SCRIPT, f"CHECK_ICON has no entry for {state}"

def test_there_is_no_legend_because_the_marks_speak_for_themselves() -> None:
    """A tracker does not ship a key to its own status icons, and every icon names itself to a
    screen reader instead."""
    from app.harness.http.console import graph_page
    from app.harness.http.graph_assets import GRAPH_SCRIPT

    page = graph_page("x")

    assert "id='legend'" not in page
    assert 'svgEl("title")' in GRAPH_SCRIPT, "every status mark carries its own name"

def test_a_person_is_the_same_disc_wherever_one_appears() -> None:
    """People stopped being nodes, but they are still drawn — on the issue they own, in the
    avatar stack, and at the top of their own panel. One factory, so they cannot drift."""
    from app.harness.http.graph_assets import GRAPH_SCRIPT

    assert GRAPH_SCRIPT.count("function avatar(") == 1
    assert GRAPH_SCRIPT.count("function initials(") == 1
    for caller in ("avatar(facts.assignee, 18)", "avatar(person.name, 22)",
                   "avatar(person.name, 18)"):
        assert caller in GRAPH_SCRIPT, f"{caller} should use the shared disc"

def test_the_toolbar_says_what_the_agent_is_doing_without_a_floating_card(
    client: TestClient,
) -> None:
    page = client.get("/console/graph").text

    assert "id='status-dot'" in page and "id='status-text'" in page
    assert "id='now'" not in page, "the dock folded into the toolbar"
    assert "function renderStatus(" in page

def test_the_tuning_constants_are_declared_once_and_marked_as_taste() -> None:
    """They were chosen because the result reads well, not because they are derived from
    anything, and the next person to touch them should know that before they start."""
    from pathlib import Path

    from app.harness.http import graph_assets

    source = Path(str(graph_assets.__file__)).read_text()
    assert "taste, not truth" in source
    assert graph_assets.GRAPH_SCRIPT.count("const TUNING = {") == 1


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
    assert "person" not in first_of


# --- the story panel's data ------------------------------------------------------------------------

async def test_every_node_carries_what_it_is_and_what_the_agent_did_about_it(
    deps: Deps,
) -> None:
    ids = await a_whole_story(deps)
    project = await deps.projects.get("acme")
    assert project is not None

    graph = await graph_data(project, deps)
    by_id = {n["id"]: n for n in graph["nodes"]}

    issue = by_id["issue:INV-26"]
    assert issue["facts"]["assignee"] == "Nodir Rahimov"
    assert issue["facts"]["filed_from_call"] is True
    assert any("filed INV-26" in e["text"] for e in issue["story"])

    check = by_id[f"task:{ids['check']}"]
    assert check["facts"]["reason"] == "is it underway?"
    assert check["facts"]["status"] == "done" and check["facts"]["early"] is True

    nodir = next(r for r in graph["roster"] if r["first_name"] == "Nodir")
    assert nodir["role"] == "backend" and nodir["owns"] == ["issue:INV-26"]

    meeting = by_id[f"meeting:{ids['event']}"]
    assert meeting["facts"]["produced"] == {"decisions": 1, "issues": 1}
    # The call owns what the tasks it started went on to do, routed through root_event_id.
    assert any("filed INV-26" in e["text"] for e in meeting["story"])

    decision = by_id[f"decision:{ids['decision']}"]
    assert decision["facts"]["statement"].startswith("Payment reminders move")
    assert decision["facts"]["source"].startswith("call @")

    lesson = by_id[f"lesson:{ids['lesson']}"]
    assert lesson["facts"]["evidence"] == ["check that INV-26 is underway"]


async def test_a_line_lands_on_the_thing_it_is_about_and_nowhere_else(deps: Deps) -> None:
    ids = await a_whole_story(deps)
    assert deps.actions is not None
    other = await deps.actions.begin(
        task_id="t-other", project_id="acme", kind="linear.create_issue",
        idempotency_key="k-other", inputs={"title": "Something unrelated"})
    await deps.actions.finish(other, target_ids={"identifier": "INV-104"}, revert={})
    project = await deps.projects.get("acme")
    assert project is not None

    by_id = {n["id"]: n for n in (await graph_data(project, deps))["nodes"]}
    here = " ".join(e["text"] for e in by_id["issue:INV-26"]["story"])
    there = " ".join(e["text"] for e in by_id["issue:INV-104"]["story"])

    assert "INV-26" in here and "INV-104" not in here
    assert "INV-104" in there and "INV-26" not in there
    assert f"task:{ids['check']}" not in here, "refs are how it attributes, not what it shows"


async def test_a_story_never_carries_a_secret_shaped_string(deps: Deps) -> None:
    await a_whole_story(deps)
    tid = await deps.queue.enqueue(
        kind="check_pr_exists", project_id="acme", payload={}, params={"issue": "INV-26"},
        reason="watch it")
    assert tid is not None
    await deps.db.update("tasks", tid, {
        "status": "failed", "error": "linear rejected the token lin_api_TOPSECRET"})
    project = await deps.projects.get("acme")
    assert project is not None

    dumped = str(await graph_data(project, deps))

    assert "lin_api_TOPSECRET" not in dumped and "[redacted]" in dumped


async def test_a_story_is_capped_so_one_busy_node_cannot_fill_the_panel(deps: Deps) -> None:
    from app.harness.http.console import STORY_LINES

    await a_whole_story(deps)
    assert deps.actions is not None
    for n in range(STORY_LINES + 8):
        action_id = await deps.actions.begin(
            task_id="t-many", project_id="acme", kind="linear.comment",
            idempotency_key=f"k-many-{n}", inputs={"title": f"comment {n}"})
        await deps.actions.finish(action_id, target_ids={"identifier": "INV-26"}, revert={})
    project = await deps.projects.get("acme")
    assert project is not None

    by_id = {n["id"]: n for n in (await graph_data(project, deps))["nodes"]}
    assert len(by_id["issue:INV-26"]["story"]) == STORY_LINES


async def test_a_graph_too_big_to_download_loses_story_before_it_loses_shape(
    deps: Deps,
) -> None:
    """The shape is the point of the page; a shorter story is still a true one."""
    from app.harness.http.console import GRAPH_BYTES, _within_budget

    fat = {
        "nodes": [
            {"id": f"task:{n}", "type": "check", "label": "x" * 60, "ts": "",
             "story": [{"ts": "", "category": "filed", "text": "y" * 400} for _ in range(12)]}
            for n in range(250)
        ],
        "edges": [], "truncated": False,
    }
    trimmed = _within_budget(fat)

    assert trimmed["truncated"] is True
    assert len(trimmed["nodes"]) == 250, "every node survives; only its story is shortened"
    assert len(json.dumps(trimmed)) <= GRAPH_BYTES


async def test_a_graph_that_fits_says_it_was_not_truncated(deps: Deps) -> None:
    await a_whole_story(deps)
    project = await deps.projects.get("acme")
    assert project is not None

    graph = await graph_data(project, deps)

    assert graph["truncated"] is False
    assert len(json.dumps(graph)) < 300_000


def test_the_page_carries_the_panel_skeleton(client: TestClient) -> None:
    page = client.get("/console/graph").text

    assert "id='panel'" in page and "id='panel-body'" in page and "id='panel-close'" in page
    for piece in (".p-key", ".p-title", ".p-head", ".p-fact", ".p-story", ".p-line", ".p-open"):
        assert piece in page, f"the sidebar needs {piece}"
    assert "Properties" in page and "Activity" in page

# --- what the agent is doing right now ------------------------------------------------------------

async def a_working_queue(deps: Deps) -> dict[str, str]:
    """One task running, two waiting their turn, one blocked behind another."""
    await deps.projects.upsert("acme", PROJECT)
    running = await deps.queue.enqueue(
        kind="check_pr_exists", project_id="acme", payload={}, params={"issue": "INV-27"},
        reason="is there a PR?")
    assert running is not None
    claimed = await deps.queue.claim(running)
    assert claimed is not None and claimed["status"] == "leased"

    soon = await deps.queue.enqueue(
        kind="check_issue_state", project_id="acme", payload={},
        params={"issue": "INV-26", "expect": ["In Progress"]}, reason="underway?",
        due_at=deps.clock.now() + timedelta(minutes=12))
    later = await deps.queue.enqueue(
        kind="check_pr_merged", project_id="acme", payload={}, params={"issue": "INV-26"},
        reason="did it land?", due_at=deps.clock.now() + timedelta(days=3))
    assert soon is not None and later is not None
    blocked = await deps.queue.enqueue(
        kind="check_pr_reviewed", project_id="acme", payload={}, params={"issue": "INV-26"},
        reason="reviewed?", depends_on=[soon])
    assert blocked is not None
    return {"running": running, "soon": soon, "later": later, "blocked": blocked}


async def test_the_graph_says_what_the_agent_is_doing_this_second(deps: Deps) -> None:
    ids = await a_working_queue(deps)
    project = await deps.projects.get("acme")
    assert project is not None

    now = (await graph_data(project, deps))["now"]

    assert now["working"]["items"] == [{
        "id": ids["running"], "kind": "check_pr_exists",
        "phrase": "looking for a pull request on INV-27", "issue": "INV-27",
        "since": "2026-08-27T09:00:00+00:00"}]
    assert now["open"] == 4 and now["watching"] == 4
    assert now["last_tick"] == ""  # nothing has finished yet


async def test_up_next_is_ordered_by_when_and_said_as_a_delta(deps: Deps) -> None:
    await a_working_queue(deps)
    project = await deps.projects.get("acme")
    assert project is not None

    up_next = (await graph_data(project, deps))["now"]["up_next"]["items"]

    assert [u["issue"] for u in up_next] == ["INV-26", "INV-26"]
    assert up_next[0]["phrase"] == "check that INV-26 is underway"
    assert up_next[0]["due_human"] == "in 12 min"
    assert up_next[1]["due_human"] == "Sun Aug 30"


async def test_waiting_names_what_it_is_waiting_for_in_words(deps: Deps) -> None:
    await a_working_queue(deps)
    project = await deps.projects.get("acme")
    assert project is not None

    waiting = (await graph_data(project, deps))["now"]["waiting"]["items"]

    assert waiting == [{"phrase": "make sure INV-26's PR gets a review",
                        "on": "check that INV-26 is underway"}]


async def test_a_phrase_never_carries_a_secret_shaped_string(deps: Deps) -> None:
    await deps.projects.upsert("acme", PROJECT)
    tid = await deps.queue.enqueue(
        kind="daily_review", project_id="acme", payload={}, params={"project": "acme"},
        reason="woken by lin_api_TOPSECRET during the tick")
    assert tid is not None
    await deps.queue.claim(tid)
    project = await deps.projects.get("acme")
    assert project is not None

    now = (await graph_data(project, deps))["now"]

    assert "lin_api_TOPSECRET" not in json.dumps(now)


async def test_each_list_shows_five_and_says_how_many_it_is_hiding(deps: Deps) -> None:
    from app.harness.http.console import NOW_LINES

    await deps.projects.upsert("acme", PROJECT)
    for n in range(NOW_LINES + 3):
        await deps.queue.enqueue(
            kind="check_pr_exists", project_id="acme", payload={}, params={"issue": f"INV-{n}"},
            reason="watch", due_at=deps.clock.now() + timedelta(hours=n + 1))
    project = await deps.projects.get("acme")
    assert project is not None

    up_next = (await graph_data(project, deps))["now"]["up_next"]

    assert len(up_next["items"]) == NOW_LINES and up_next["more"] == 3


async def test_an_empty_project_still_reports_an_honest_now(
    client: TestClient, deps: Deps
) -> None:
    async def nothing(slug: str) -> None:
        return None

    deps.projects.get = nothing  # type: ignore[method-assign]
    now = client.get("/console/graph.json").json()["now"]

    assert now["working"]["items"] == [] and now["up_next"]["items"] == []
    assert now["open"] == 0 and now["last_tick"] == ""


def test_every_kind_the_agent_runs_can_say_what_it_is_doing() -> None:
    """The dock shows this while it happens, so a kind with no present tense would surface as a
    raw slug on the one screen that is always open."""
    from app.harness.kinds.phrasing import WORKING_SENTENCES
    from app.harness.kinds.registry import KINDS
    from app.harness.stages.runner import STAGES

    unsayable = (set(KINDS) | set(STAGES)) - set(WORKING_SENTENCES) - {"reconcile_item"}
    assert unsayable == set(), f"no present tense for: {unsayable}"


def test_the_now_line_and_its_pill_are_on_the_page(client: TestClient) -> None:
    page = client.get("/console/graph").text

    assert "#nowline" in page and "id='nowtag'" in page
    assert "id='now-btn'" in page, "a way back to the now line"

def test_the_dock_never_polls_while_the_reader_is_in_the_past(client: TestClient) -> None:
    page = client.get("/console/graph").text

    assert "if (!atLive() || playing) return;" in page
    assert "window.setInterval(poll, 60000)" in page


# --- duplicates already in the ledger ---------------------------------------------------------

async def test_a_decision_recorded_twice_before_the_guard_existed_draws_one_node(
    deps: Deps,
) -> None:
    """The production ledger holds pairs written before the write-side guard, and nobody is
    rewriting those documents. The graph collapses them on the way out instead."""
    ids = await a_whole_story(deps)
    twin = "d-twin"
    await deps.db.create("decisions", twin, {
        "statement": "Payment reminders move to three days after due.",
        "rejected_options": [], "source": "fathom:8841201@00:04:10",
        "quote": "so, three days after due", "also_quoted": [], "meeting_title": "",
        "meeting_url": "", "linked_issue_ids": [], "project_id": "acme",
        "event_id": ids["event"], "created_at": "2026-08-27T10:05:00+00:00"})
    project = await deps.projects.get("acme")
    assert project is not None

    graph = await graph_data(project, deps)
    decisions = [n for n in graph["nodes"] if n["type"] == "decision"]

    assert len(decisions) == 1
    assert decisions[0]["id"] == f"decision:{ids['decision']}", "the cited one survives"
    assert not any(n["id"] == f"decision:{twin}" for n in graph["nodes"])


async def test_collapsing_a_duplicate_never_orphans_the_lines_drawn_to_it(deps: Deps) -> None:
    ids = await a_whole_story(deps)
    await deps.db.create("decisions", "d-twin", {
        "statement": "Payment reminders move to three days after due.",
        "rejected_options": [], "source": "", "quote": "", "also_quoted": [],
        "meeting_title": "", "meeting_url": "", "linked_issue_ids": [], "project_id": "acme",
        "event_id": ids["event"], "created_at": "2026-08-27T10:05:00+00:00"})
    project = await deps.projects.get("acme")
    assert project is not None

    graph = await graph_data(project, deps)
    drawn = {n["id"] for n in graph["nodes"]}

    assert all(e["source"] in drawn and e["target"] in drawn for e in graph["edges"])


async def test_two_genuinely_different_decisions_both_reach_the_graph(deps: Deps) -> None:
    ids = await a_whole_story(deps)
    await deps.db.create("decisions", "d-other", {
        "statement": "Ship the invoice CSV export behind a feature flag.",
        "rejected_options": [], "source": "", "quote": "", "also_quoted": [],
        "meeting_title": "", "meeting_url": "", "linked_issue_ids": [], "project_id": "acme",
        "event_id": ids["event"], "created_at": "2026-08-27T10:05:00+00:00"})
    project = await deps.projects.get("acme")
    assert project is not None

    graph = await graph_data(project, deps)

    assert len([n for n in graph["nodes"] if n["type"] == "decision"]) == 2


# --- the diagram's data ---------------------------------------------------------------------------

async def test_a_scheduled_check_carries_what_the_future_column_needs(deps: Deps) -> None:
    """A check that has not run yet is drawn in the column of the day it is due, hollow, with a
    dashed ring when it is waiting on another check. All three come from the document."""
    ids = await a_whole_story(deps)
    blocked = await deps.db.get("tasks", ids["dependent"])
    assert blocked is not None
    await deps.db.update("tasks", ids["dependent"],
                         {"due_at": "2026-09-03T16:00:00+00:00", "status": "blocked"})
    project = await deps.projects.get("acme")
    assert project is not None

    graph = await graph_data(project, deps)
    node = next(n for n in graph["nodes"] if n["id"] == f"task:{ids['dependent']}")

    assert node["state"] == "blocked"
    assert node["due_day"] == "2026-09-03"
    assert node["day"] == "2026-09-03", "it sits on the day it will run"
    assert node["waits_on"] == [f"task:{ids['check']}"]


async def test_a_check_that_already_ran_reports_how_it_went(deps: Deps) -> None:
    ids = await a_whole_story(deps)
    project = await deps.projects.get("acme")
    assert project is not None

    graph = await graph_data(project, deps)
    node = next(n for n in graph["nodes"] if n["id"] == f"task:{ids['check']}")

    assert node["state"] == "early"


async def test_a_call_card_carries_the_strip_that_says_how_far_it_got(deps: Deps) -> None:
    ids = await a_whole_story(deps)
    project = await deps.projects.get("acme")
    assert project is not None

    graph = await graph_data(project, deps)
    call = next(n for n in graph["nodes"] if n["id"] == f"meeting:{ids['event']}")

    assert [s["name"] for s in call["stages"]] == [
        "read", "triaged", "reconciled", "filed", "planned"]


async def test_every_node_lands_in_a_day_that_has_a_column(deps: Deps) -> None:
    """A node whose day has no column would be positioned off the diagram and never seen."""
    await a_whole_story(deps)
    project = await deps.projects.get("acme")
    assert project is not None

    graph = await graph_data(project, deps)
    columns = {d["key"] for d in graph["days"]}

    assert all(n["day"] in columns for n in graph["nodes"])
    assert all(d["key"] in graph["widths"] for d in graph["days"])


def test_only_two_relationships_are_allowed_to_cross_the_columns(client: TestClient) -> None:
    """Everything else drawn across the diagram would turn it back into the hairball this
    replaced. The rule lives in one place and says why."""
    page = client.get("/console/graph").text

    assert 'edge.rel !== "waits on" && edge.rel !== "led to"' in page
    assert "hairball" in page


def test_threads_are_drawn_under_the_chips_not_over_them(client: TestClient) -> None:
    """A thread crossing the title of the thing it points at makes both unreadable."""
    page = client.get("/console/graph").text

    assert "#canvas { position:absolute; top:0; left:0; overflow:visible; z-index:2" in page
    assert "#layer { position:absolute; top:0; left:0; z-index:1; }" in page
    assert ".n { z-index:3; }" in page


def test_nothing_is_drawn_between_nodes_until_you_ask(client: TestClient) -> None:
    """Structure is carried by alignment. The only line at rest is a dependency between two
    checks, which is the one relationship the columns cannot show on their own."""
    page = client.get("/console/graph").text

    assert ".edge { fill:none; stroke-width:1; opacity:0;" in page
    assert ".edge.dep { opacity:.55;" in page
    assert ".edge.lit { opacity:.9;" in page

def test_a_thread_stops_at_the_rim_of_what_it_points_at(client: TestClient) -> None:
    page = client.get("/console/graph").text

    assert "function halfOf(node)" in page
    assert "const from = a.y + (down ? halfOf(a) : -halfOf(a));" in page


def test_a_dependency_across_the_whole_week_waits_to_be_asked_for(client: TestClient) -> None:
    """It is true and it is unreadable: at rest it is one page-wide horizontal rule. The check
    already says "due Aug 31, resolved Aug 27" on its face."""
    page = client.get("/console/graph").text

    assert "longEdgeColumns:" in page
    assert "function columnsApart(a, b)" in page



def test_the_page_explains_its_own_rows_to_a_stranger(client: TestClient) -> None:
    """"Understood" is opaque to a first-time reviewer, and they are the whole audience."""
    page = client.get("/console/graph").text

    for about in ("calls and asks that came in", "decisions and disagreements",
                  "issues filed, messages sent", "checks — past and scheduled",
                  "lessons from its own record"):
        assert about in page
    assert "Nothing yet — lessons come from the daily review" in page
    assert ".lane-about" in page


def test_a_conversation_gets_its_own_strip_on_the_page(client: TestClient) -> None:
    page = client.get("/console/graph").text

    assert ".strip-rule" in page
    assert "function producedRows(" in page
    assert ".hair-label" in page, "the row of dots says what it is"


def test_the_controls_say_what_they_do(client: TestClient) -> None:
    page = client.get("/console/graph").text

    assert "▶ Replay the story" in page
    assert "Rebuilds the page from the first event, in order" in page
    assert "Scroll to the present" in page
    assert 'event.key === "Escape"' in page, "Esc closes the panel"


def test_a_replayed_call_keeps_its_work_under_its_own_card(deps: Deps) -> None:
    """A webhook replayed through the replay script carries `#retry2` on its root event id. It
    is the same call, and leaving the suffix on split its issues into a nameless second strip
    beside the card that produced them."""
    from app.harness.http.console import _origin

    assert _origin("fathom:abc#retry2") == "fathom:abc"
    assert _origin("fathom:abc#retry10") == "fathom:abc"
    assert _origin("fathom:abc") == "fathom:abc"
    assert _origin("") == ""
    assert _origin("fathom:not#retryX") == "fathom:not#retryX", "only a real retry suffix goes"


async def test_a_retried_call_and_its_issues_share_one_strip(deps: Deps) -> None:
    ids = await a_whole_story(deps)
    task = await deps.db.get("tasks", ids["check"])
    assert task is not None
    # the act task that filed INV-26, as a replay would have left it
    for row in await deps.db.query("tasks", [("project_id", "==", "acme")]):
        if row.get("root_event_id"):
            await deps.db.update("tasks", str(row["id"]),
                                 {"root_event_id": f"{row['root_event_id']}#retry2"})
    project = await deps.projects.get("acme")
    assert project is not None

    graph = await graph_data(project, deps)
    by_id = {n["id"]: n for n in graph["nodes"]}

    call = by_id[f"meeting:{ids['event']}"]
    issue = by_id["issue:INV-26"]
    assert issue["group"] == call["group"], "the replayed run belongs to the call it replayed"
    assert issue["group"] != "day"


def test_the_page_scrolls_rather_than_cramming_the_week_in(client: TestClient) -> None:
    """A page that fits by cutting "Sprint 1 kickoff sync" into two words has traded the only
    thing it was for. Nothing is squeezed below its readable width."""
    page = client.get("/console/graph").text

    assert "cardFloor" not in page and "chipFloor" not in page, "no squeezing pass left"
    assert "anchor: 0.65" in page
    assert "event.shiftKey" in page, "shift-wheel scrolls the week"
    assert "#gutter { position:fixed" in page, "the lane names stay put while it scrolls"


def test_a_narrow_strip_shows_dots_without_a_caption(client: TestClient) -> None:
    page = client.get("/console/graph").text

    assert "labelAt:" in page
    assert "strip.width < TUNING.labelAt" in page


def test_a_half_scrolled_day_still_shows_its_date(client: TestClient) -> None:
    """The label used to be pinned to the column's left edge, so a day scrolled halfway off
    lost its date entirely and the visible past had no name."""
    page = client.get("/console/graph").text

    assert "function stickHeaders(" in page
    assert "Math.min(Math.max(column.x, leftEdge), right - 96)" in page
    assert "stickHeaders();" in page


def test_the_week_opens_at_its_right_end(client: TestClient) -> None:
    """The last scheduled day flush to the edge: every pixel on the left is then spent on
    history rather than on empty ground past the last check."""
    page = client.get("/console/graph").text

    assert "setPan(worldWidth <= stage.clientWidth ? 0 : stage.clientWidth - worldWidth);" in page
    assert 'nowButton.addEventListener("click", openingView);' in page


def test_the_grid_ends_where_the_work_ends(client: TestClient) -> None:
    page = client.get("/console/graph").text

    assert "contentHeight = y + 24;" in page
    assert 'ground.style.height = contentHeight + "px";' in page
    assert 'rule.style.height = contentHeight + "px";' in page


async def test_a_check_pill_carries_the_owner_who_will_answer_it(deps: Deps) -> None:
    """A check nobody owns is a check nobody answers, so the person is part of what it is.
    The owner map is keyed by node id, which is what this used to get wrong."""
    ids = await a_whole_story(deps)
    project = await deps.projects.get("acme")
    assert project is not None

    graph = await graph_data(project, deps)
    check = next(n for n in graph["nodes"] if n["id"] == f"task:{ids['check']}")

    assert check["facts"]["assignee"] == "Nodir Rahimov"
    assert check["facts"]["issue"] == "INV-26"
    assert "on_unmet" in check["facts"], "and a place to say what happens if it is not met"


def test_the_check_chip_draws_that_owner(client: TestClient) -> None:
    page = client.get("/console/graph").text

    assert 'if (node.type === "check" && owner) chip.appendChild(avatar(String(owner), 18));' \
        in page
    assert 'body.appendChild(el("div", "from", "from: " + node.from_call));' in page
