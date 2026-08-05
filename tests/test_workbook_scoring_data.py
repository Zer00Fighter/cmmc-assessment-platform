from pathlib import Path

import pytest

from src.workbook import (
    WorkbookScoringData,
    WorkbookScoringDataError,
)


ROOT = Path(__file__).resolve().parents[1]

SCORING_PATH = (
    ROOT
    / "data"
    / "scoring"
    / "scoring_weights.csv"
)


def test_loads_110_scoring_rules() -> None:
    loader = WorkbookScoringData(
        SCORING_PATH
    )

    rules = loader.load()

    assert len(rules) == 110


def test_rules_are_unique() -> None:
    rules = WorkbookScoringData(
        SCORING_PATH
    ).load()

    requirement_ids = [
        rule.requirement_id
        for rule in rules
    ]

    assert len(requirement_ids) == len(
        set(requirement_ids)
    )


def test_load_map_contains_first_requirement() -> None:
    rule_map = WorkbookScoringData(
        SCORING_PATH
    ).load_map()

    assert "AC.L2-3.1.1" in rule_map
    assert (
        rule_map[
            "AC.L2-3.1.1"
        ].full_deduction_points
        in {1, 3, 5}
    )


def test_only_two_partial_credit_rules() -> None:
    rules = WorkbookScoringData(
        SCORING_PATH
    ).load()

    partial_rules = [
        rule
        for rule in rules
        if rule.partial_credit_allowed
    ]

    assert len(partial_rules) == 2

    assert {
        rule.requirement_id
        for rule in partial_rules
    } == {
        "IA.L2-3.5.3",
        "SC.L2-3.13.11",
    }


def test_partial_credit_values() -> None:
    rule_map = WorkbookScoringData(
        SCORING_PATH
    ).load_map()

    for requirement_id in {
        "IA.L2-3.5.3",
        "SC.L2-3.13.11",
    }:
        rule = rule_map[requirement_id]

        assert rule.partial_deduction_points == 3
        assert rule.full_deduction_points == 5


def test_missing_scoring_file_is_rejected(
    tmp_path: Path,
) -> None:
    loader = WorkbookScoringData(
        tmp_path / "missing.csv"
    )

    with pytest.raises(
        FileNotFoundError,
        match="Scoring weights CSV",
    ):
        loader.load()


def test_invalid_boolean_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "invalid.csv"

    path.write_text(
        "requirement_id,domain_code,"
        "scoring_category,deduction_points,"
        "partial_credit_allowed,"
        "partial_deduction_points,"
        "full_deduction_points,"
        "partial_credit_condition,"
        "full_deduction_condition,"
        "scoring_source,"
        "scoring_source_version\n"
        "AC.L2-3.1.1,AC,FIVE_POINT,5,"
        "Maybe,0,5,,Not met,Test,Test\n",
        encoding="utf-8",
    )

    loader = WorkbookScoringData(path)

    with pytest.raises(
        WorkbookScoringDataError,
        match="Unsupported Boolean value",
    ):
        loader.load()
        