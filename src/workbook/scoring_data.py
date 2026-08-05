from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


class WorkbookScoringDataError(ValueError):
    """Raised when workbook scoring source data is invalid."""


@dataclass(frozen=True)
class WorkbookScoringRule:
    """Scoring configuration used by the Excel workbook."""

    requirement_id: str
    domain_code: str
    scoring_category: str
    deduction_points: int
    partial_credit_allowed: bool
    partial_deduction_points: int
    full_deduction_points: int
    partial_credit_condition: str
    full_deduction_condition: str
    scoring_source: str
    scoring_source_version: str


class WorkbookScoringData:
    """
    Load and validate scoring rules used by the workbook generator.

    This class is intentionally separate from the assessment and scoring
    engines. Its purpose is to provide clean, workbook-ready scoring data.
    """

    EXPECTED_RULE_COUNT = 110

    REQUIRED_COLUMNS = {
        "requirement_id",
        "domain_code",
        "scoring_category",
        "deduction_points",
        "partial_credit_allowed",
        "partial_deduction_points",
        "full_deduction_points",
        "partial_credit_condition",
        "full_deduction_condition",
        "scoring_source",
        "scoring_source_version",
    }

    VALID_CATEGORIES = {
        "ONE_POINT",
        "THREE_POINT",
        "FIVE_POINT",
        "PARTIAL_3_OR_5",
    }

    def __init__(
        self,
        scoring_weights_csv: Path,
    ) -> None:
        self.scoring_weights_csv = (
            scoring_weights_csv.resolve()
        )

    def load(self) -> List[WorkbookScoringRule]:
        if not self.scoring_weights_csv.exists():
            raise FileNotFoundError(
                "Scoring weights CSV was not found: "
                f"{self.scoring_weights_csv}. "
                "Run python compile_scoring.py first."
            )

        with self.scoring_weights_csv.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            if reader.fieldnames is None:
                raise WorkbookScoringDataError(
                    "Scoring weights CSV has no header."
                )

            missing_columns = (
                self.REQUIRED_COLUMNS
                - set(reader.fieldnames)
            )

            if missing_columns:
                raise WorkbookScoringDataError(
                    "Scoring weights CSV is missing columns: "
                    + ", ".join(
                        sorted(missing_columns)
                    )
                )

            rows = list(reader)

        rules = [
            self._parse_rule(row)
            for row in rows
        ]

        self._validate_rules(rules)

        return rules

    def load_map(
        self,
    ) -> Dict[str, WorkbookScoringRule]:
        rules = self.load()

        return {
            rule.requirement_id: rule
            for rule in rules
        }

    def _parse_rule(
        self,
        row: Dict[str, str],
    ) -> WorkbookScoringRule:
        requirement_id = self._normalize_requirement_id(
            row["requirement_id"]
        )

        try:
            deduction_points = int(
                row["deduction_points"]
            )

            partial_deduction_points = int(
                row["partial_deduction_points"]
            )

            full_deduction_points = int(
                row["full_deduction_points"]
            )

        except ValueError as error:
            raise WorkbookScoringDataError(
                "Invalid numeric scoring data for "
                f"{requirement_id}."
            ) from error

        return WorkbookScoringRule(
            requirement_id=requirement_id,
            domain_code=(
                row["domain_code"]
                .strip()
                .upper()
            ),
            scoring_category=(
                row["scoring_category"]
                .strip()
                .upper()
            ),
            deduction_points=deduction_points,
            partial_credit_allowed=(
                self._parse_bool(
                    row[
                        "partial_credit_allowed"
                    ]
                )
            ),
            partial_deduction_points=(
                partial_deduction_points
            ),
            full_deduction_points=(
                full_deduction_points
            ),
            partial_credit_condition=(
                row[
                    "partial_credit_condition"
                ].strip()
            ),
            full_deduction_condition=(
                row[
                    "full_deduction_condition"
                ].strip()
            ),
            scoring_source=(
                row["scoring_source"].strip()
            ),
            scoring_source_version=(
                row[
                    "scoring_source_version"
                ].strip()
            ),
        )

    def _validate_rules(
        self,
        rules: List[WorkbookScoringRule],
    ) -> None:
        if len(rules) != self.EXPECTED_RULE_COUNT:
            raise WorkbookScoringDataError(
                f"Expected {self.EXPECTED_RULE_COUNT} "
                "scoring rules, but found "
                f"{len(rules)}."
            )

        requirement_ids = [
            rule.requirement_id
            for rule in rules
        ]

        if len(requirement_ids) != len(
            set(requirement_ids)
        ):
            raise WorkbookScoringDataError(
                "Duplicate requirement IDs exist in "
                "the scoring weights CSV."
            )

        for rule in rules:
            self._validate_rule(rule)

    def _validate_rule(
        self,
        rule: WorkbookScoringRule,
    ) -> None:
        expected_domain = (
            rule.requirement_id[:2]
        )

        if rule.domain_code != expected_domain:
            raise WorkbookScoringDataError(
                f"{rule.requirement_id} has domain "
                f"{rule.domain_code}; expected "
                f"{expected_domain}."
            )

        if (
            rule.scoring_category
            not in self.VALID_CATEGORIES
        ):
            raise WorkbookScoringDataError(
                f"{rule.requirement_id} has invalid "
                "scoring category "
                f"{rule.scoring_category}."
            )

        if rule.deduction_points not in {
            1,
            3,
            5,
        }:
            raise WorkbookScoringDataError(
                f"{rule.requirement_id} has invalid "
                "deduction points "
                f"{rule.deduction_points}."
            )

        if rule.full_deduction_points not in {
            1,
            3,
            5,
        }:
            raise WorkbookScoringDataError(
                f"{rule.requirement_id} has invalid "
                "full deduction points "
                f"{rule.full_deduction_points}."
            )

        if rule.partial_credit_allowed:
            if (
                rule.scoring_category
                != "PARTIAL_3_OR_5"
            ):
                raise WorkbookScoringDataError(
                    f"{rule.requirement_id} permits "
                    "partial credit but is not categorized "
                    "as PARTIAL_3_OR_5."
                )

            if (
                rule.partial_deduction_points != 3
                or rule.full_deduction_points != 5
            ):
                raise WorkbookScoringDataError(
                    f"{rule.requirement_id} has invalid "
                    "partial-credit values."
                )

        elif rule.partial_deduction_points != 0:
            raise WorkbookScoringDataError(
                f"{rule.requirement_id} does not permit "
                "partial credit but has a nonzero "
                "partial deduction."
            )

    @staticmethod
    def _parse_bool(
        value: str,
    ) -> bool:
        normalized = (
            value.strip().lower()
        )

        if normalized in {
            "yes",
            "true",
            "1",
            "y",
        }:
            return True

        if normalized in {
            "no",
            "false",
            "0",
            "n",
        }:
            return False

        raise WorkbookScoringDataError(
            f"Unsupported Boolean value: {value}"
        )

    @staticmethod
    def _normalize_requirement_id(
        requirement_id: str,
    ) -> str:
        normalized = (
            requirement_id
            .strip()
            .upper()
        )

        if (
            len(normalized) >= 6
            and normalized[2:6] == "-L2-"
        ):
            normalized = (
                normalized[:2]
                + ".L2-"
                + normalized[6:]
            )

        return normalized