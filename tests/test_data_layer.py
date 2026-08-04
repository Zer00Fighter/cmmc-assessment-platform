from pathlib import Path

from src.loaders.csv_loader import (
    load_controls,
    load_domains,
    load_objectives,
)


ROOT = Path(__file__).resolve().parents[1]


def test_domains_load() -> None:
    domains = load_domains(
        ROOT / "data" / "controls" / "domains.csv"
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

    assert len(controls) >= 1
    assert controls[0].requirement_id == "AC.L2-3.1.1"
    assert controls[0].deduction_points in {1, 3, 5}


def test_objectives_load() -> None:
    objectives = load_objectives(
        ROOT
        / "data"
        / "controls"
        / "cmmc_level2_objectives.csv"
    )

    assert len(objectives) >= 1
    assert objectives[0].requirement_id == "AC.L2-3.1.1"