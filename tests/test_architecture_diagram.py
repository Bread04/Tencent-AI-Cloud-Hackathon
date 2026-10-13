"""Seam: the diagram deliverables (ticket 17), made with Archify and kept in `docs/diagrams/`.

Each diagram is a typed description (`*.archify.json`) that Archify renders to a standalone page (`*.html`) and
checks itself. These tests check what Archify cannot know: that the description still matches this system.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.demo import create_demo_app
from src.api.demo_switches import DEMO_SWITCHES
from src.api.walkthrough import STEPS

ROOT = Path(__file__).resolve().parents[1]
DIAGRAMS = ROOT / "docs" / "diagrams"
CORE, SUPPORTING, STORE, SIMULATED, PERSON = "backend", "cloud", "database", "external", "security"  # the Archify type each kind is drawn as; the legend renames them


@pytest.fixture(scope="module")
def architecture():
    return json.loads((DIAGRAMS / "architecture.archify.json").read_text(encoding="utf-8"))


def drawn_as(diagram, kind):
    return [part for part in diagram["components"] if part["type"] == kind]


def test_the_three_core_agents_and_only_those_are_drawn_as_core(architecture):
    assert sorted(part["label"] for part in drawn_as(architecture, CORE)) == ["Driver Advocate", "Judge", "Rider Advocate"]
    assert all("Core Agent" in part["sublabel"] for part in drawn_as(architecture, CORE))


def test_the_case_store_sits_in_the_middle_with_parts_on_every_side(architecture):
    (store,) = drawn_as(architecture, STORE)
    left, top = store["pos"]
    right, bottom = left + store["size"][0], top + store["size"][1]
    others = [part["pos"] for part in architecture["components"] if part is not store]

    assert store["label"] == "Case store"
    assert any(x < left for x, _ in others) and any(x >= right for x, _ in others)
    assert any(y < top for _, y in others) and any(y >= bottom for _, y in others)


def test_every_switch_in_the_console_is_a_supporting_agent_that_names_its_checkbox(architecture):
    named = [part["sublabel"] for part in drawn_as(architecture, SUPPORTING)]

    for switch in DEMO_SWITCHES:
        assert f"switch: {switch.label}" in named, switch.label
    assert "Escalation Protocol" in [part["label"] for part in drawn_as(architecture, SUPPORTING)]  # on for every run, so it has no checkbox


@pytest.mark.parametrize("part", ["Trip records", "Photos", "Policy, past Rulings", "Payment action"])
def test_each_simulated_component_says_it_is_simulated_where_it_is_always_visible(architecture, part):
    (found,) = [p for p in drawn_as(architecture, SIMULATED) if p["label"] == part]

    assert found["sublabel"].startswith("simulated")  # the sublabel, not the tag: a tag only shows when zoomed in


def test_the_human_review_path_the_log_and_the_orchestrator_are_shown(architecture):
    labels = {part["label"] for part in architecture["components"]}
    flows = {(c["from"], c["to"]) for c in architecture["connections"]}

    assert {"Human Reviewer", "Communication Log", "Orchestrator", "Learning Feedback Loop"} <= labels
    assert [part["label"] for part in drawn_as(architecture, PERSON)] == ["Human Reviewer"]
    assert {("escalation", "reviewer"), ("reviewer", "outcome"), ("reviewer", "learning"), ("store", "log")} <= flows


def test_the_legend_names_each_kind_in_the_projects_own_words(architecture):
    entries = architecture["meta"]["legend"]["entries"]

    assert entries[CORE]["label"] == "Core Agent" and entries[SIMULATED]["label"] == "Simulated"
    assert entries[SUPPORTING]["label"].startswith("Supporting Agent")


def test_every_source_the_diagrams_cite_is_a_file_in_this_repository():
    for name in ("architecture.archify.json", "demo-walkthrough.archify.json"):
        diagram = json.loads((DIAGRAMS / name).read_text(encoding="utf-8"))
        for part in diagram.get("components", diagram.get("nodes")):
            for source in part["sources"]:
                assert (ROOT / source["path"]).is_file(), f"{name}: {source['path']}"


def test_the_walkthrough_diagram_has_one_box_per_step_of_the_walkthrough_in_order_naming_its_dispute_and_switch():
    diagram = json.loads((DIAGRAMS / "demo-walkthrough.archify.json").read_text(encoding="utf-8"))
    labels = {s.name: s.label for s in DEMO_SWITCHES}
    steps = [node for node in diagram["nodes"] if node["label"][0].isdigit()]

    assert [node["label"] for node in steps] == [f"{number}. {step.dispute_id}" for number, step in enumerate(STEPS, start=1)]
    for node, step in zip(steps, STEPS):
        for name in step.tick:
            assert node["sublabel"] == f"tick {labels[name]}", node["label"]


@pytest.mark.parametrize("name", ["architecture", "demo-walkthrough"])
def test_each_diagram_has_its_rendered_page_and_a_picture_for_the_readme(name):
    page = (DIAGRAMS / f"{name}.html").read_text(encoding="utf-8")
    title = json.loads((DIAGRAMS / f"{name}.archify.json").read_text(encoding="utf-8"))["meta"]["title"]

    assert title in page and "<svg" in page
    assert (DIAGRAMS / f"{name}.png").stat().st_size > 10_000


# --- shown in the app, one click from the console -------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    return TestClient(create_demo_app())


def test_the_app_serves_the_architecture_diagram(client, architecture):
    page = client.get("/architecture")

    assert page.status_code == 200 and page.headers["content-type"].startswith("text/html")
    assert architecture["meta"]["title"] in page.text and "Case store" in page.text


@pytest.mark.parametrize("path", ["/", "/review", "/evaluation"])
def test_every_page_of_the_console_links_to_the_diagram(client, path):
    assert 'href="/architecture"' in client.get(path).text


def test_the_readme_and_the_architecture_doc_show_the_diagram_and_point_at_the_demo_script():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/diagrams/architecture.png" in readme and "docs/diagrams/architecture.html" in readme
    assert "docs/demo-script.md" in readme
    assert "diagrams/architecture.png" in (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
