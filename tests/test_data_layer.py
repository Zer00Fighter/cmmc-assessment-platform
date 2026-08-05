from pathlib import Path

from src.loaders.csv_loader import (
    load_controls,
    load_domains,
    load_objectives,
)


ROOT = Path(__file__).resolve().parents[1]


def test_domains_load() -> None:
    domains = load_domains(
        ROOT
        / "data"
        / "controls"
        / "domains.csv"
    )

    assert len(domains) == 14
    assert domains[0].code == "AC"
    assert domains[-1].code == "SI"


def test_controls_load() -> None:
    controls = load_controls(
        ROOT
        / "data"
        / "controls"
        / "cmmc_level2_controls.csv"
    )

    assert len(controls) == 110

    first = controls[0]
    last = controls[-1]

    assert first.requirement_id == "AC.L2-3.1.1"
    assert first.domain_code == "AC"
    assert first.statement
    assert first.source_page_start > 0
    assert first.source_page_end >= first.source_page_start
    assert first.source_version == "2.13"

    assert last.requirement_id == "SI.L2-3.14.7"


def test_objectives_load() -> None:
    objectives = load_objectives(
        ROOT
        / "data"
        / "controls"
        / "cmmc_level2_objectives.csv"
    )

    assert len(objectives) > 110

    first = objectives[0]

    assert first.requirement_id == "AC.L2-3.1.1"
    assert first.objective_id == "a"
    assert first.objective_text
    assert first.source_page_start > 0
    assert first.source_page_end >= first.source_page_start


def test_first_requirement_has_six_objectives() -> None:
    objectives = load_objectives(
        ROOT
        / "data"
        / "controls"
        / "cmmc_level2_objectives.csv"
    )

    first_requirement_objectives = [
        objective
        for objective in objectives
        if objective.requirement_id == "AC.L2-3.1.1"
    ]

    assert len(first_requirement_objectives) == 6

    assert [
        objective.objective_id
        for objective in first_requirement_objectives
    ] == [
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
    ]