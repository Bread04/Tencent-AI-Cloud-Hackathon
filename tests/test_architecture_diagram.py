"""Seam: the architecture diagram deliverable (ticket 17): `docs/architecture-diagram.svg` and the page that shows it."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.demo import create_demo_app
from src.api.demo_switches import DEMO_SWITCHES

DIAGRAM = Path(__file__).resolve().parents[1] / "docs" / "architecture-diagram.svg"
SVG = "{http://www.w3.org/2000/svg}"


def words(element) -> str:
    return " ".join(" ".join(element.itertext()).split())


@pytest.fixture(scope="module")
def root():
    return ET.parse(DIAGRAM).getroot()  # parsing proves it is well-formed


def boxes(root, kind: str) -> list[str]:
    """The text of every component drawn as this kind (`core`, `supporting`, `simulated`...)."""
    return [words(g) for g in root.iter(f"{SVG}g") if kind in g.get("class", "").split()]


def test_the_diagram_is_an_svg_with_a_title_and_a_description_for_people_who_cannot_see_it(root):
    assert root.tag == f"{SVG}svg" and root.get("viewBox")
    assert root.find(f"{SVG}title") is not None and len(words(root.find(f"{SVG}desc"))) > 100


def test_the_three_core_agents_and_only_those_are_drawn_as_core(root):
    core = boxes(root, "core")

    assert len(core) == 3
    for name in ("Rider Advocate", "Driver Advocate", "Judge"):
        assert any(name in box for box in core)


def test_the_case_store_sits_in_the_middle_of_the_diagram(root):
    (store,) = [g for g in root.iter(f"{SVG}g") if "store" in g.get("class", "").split()]
    shape = store.find(f"{SVG}rect")
    centre_x = float(shape.get("x")) + float(shape.get("width")) / 2
    centre_y = float(shape.get("y")) + float(shape.get("height")) / 2
    _, _, width, height = (float(n) for n in root.get("viewBox").split())

    assert "Case store" in words(store)
    assert abs(centre_x - width / 2) < width * 0.05 and abs(centre_y - height / 2) < height * 0.15


def test_every_switch_in_the_console_is_a_supporting_agent_in_the_diagram_named_by_its_checkbox(root):
    supporting = " | ".join(boxes(root, "supporting"))

    for switch in DEMO_SWITCHES:
        assert switch.label in supporting, switch.label
    assert "Escalation" in supporting  # on for every run, so it has no checkbox


@pytest.mark.parametrize("part", ["Human Reviewer", "Review queue", "Communication Log", "Orchestrator"])
def test_the_human_review_path_the_log_and_the_orchestrator_are_shown(root, part):
    assert part in words(root)


@pytest.mark.parametrize("part", ["Trip records", "Policy", "Payment", "Past rulings", "Photos", "Outcome to both parties"])
def test_each_simulated_component_is_marked_as_simulated(root, part):
    marked = [box for box in boxes(root, "simulated") if part in box]

    assert marked and all("SIMULATED" in box for box in marked)


def test_the_legend_explains_every_kind_of_box(root):
    (legend,) = [words(g) for g in root.iter(f"{SVG}g") if g.get("class") == "legend"]

    for kind in ("Core Agent", "Supporting Agent", "Code, not a model", "Simulated"):
        assert kind in legend


def test_the_diagram_is_self_contained_so_it_renders_the_same_on_github_and_on_a_projector():
    text = DIAGRAM.read_text(encoding="utf-8")

    assert "<script" not in text and "<image" not in text and "@import" not in text and "<foreignObject" not in text
    assert "href=\"http" not in text


# --- shown in the app, one click from the console -------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    return TestClient(create_demo_app())


def test_the_app_shows_the_diagram_on_its_own_page_labelled_as_simulated(client):
    page = client.get("/architecture")

    assert page.status_code == 200
    assert "<svg" in page.text and "Case store" in page.text
    assert "mock data" in page.text.lower()


@pytest.mark.parametrize("path", ["/", "/review", "/evaluation", "/architecture"])
def test_every_page_of_the_console_links_to_the_diagram(client, path):
    assert 'href="/architecture"' in client.get(path).text


def test_the_readme_and_the_architecture_doc_show_the_diagram_and_point_at_the_demo_script():
    docs = DIAGRAM.parent

    assert "docs/architecture-diagram.svg" in (docs.parent / "README.md").read_text(encoding="utf-8")
    assert "docs/demo-script.md" in (docs.parent / "README.md").read_text(encoding="utf-8")
    assert "architecture-diagram.svg" in (docs / "architecture.md").read_text(encoding="utf-8")


def test_the_diagrams_styles_apply_only_inside_it_so_the_page_that_shows_it_is_not_restyled(root):
    rules = [line.split("{")[0] for line in root.find(f".//{SVG}style").text.splitlines() if "{" in line]

    assert rules and root.get("class") == "architecture-diagram"
    assert all(selector.strip().startswith(".architecture-diagram ") for rule in rules for selector in rule.split(","))
