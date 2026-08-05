from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Sequence

from src.scoring.scoring_compiler import (
    EXPECTED_FIVE_POINT_COUNT,
    EXPECTED_MAXIMUM_DEDUCTION,
    EXPECTED_MINIMUM_SCORE,
    EXPECTED_ONE_POINT_COUNT,
    EXPECTED_PARTIAL_CREDIT_COUNT,
    EXPECTED_REQUIREMENT_COUNT,
    EXPECTED_THREE_POINT_COUNT,
    FIVE_POINT_REQUIREMENTS,
    MAXIMUM_SCORE,
    PARTIAL_CREDIT_REQUIREMENTS,
    THREE_POINT_REQUIREMENTS,
)
from src.scoring.scoring_engine import ScoringRule


class ScoringValidationError(RuntimeError):
    """Raised when the scoring configuration fails validation."""


@dataclass(frozen=True)
class ScoringValidationIssue:
    severity: str
    code: str
    message: str
    requirement_id: str = ""


@dataclass
class ScoringValidationReport:
    rule_count: int
    category_counts: Dict[str, int]
    total_possible_deduction: int
    minimum_score: int
    errors: List[ScoringValidationIssue] = field(
        default_factory=list
    )
    warnings: List[ScoringValidationIssue] = field(
        default_factory=list
    )

    @property
    def passed(self) -> bool:
        return not self.errors

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def raise_for_errors(self) -> None:
        if self.passed:
            return

        details = "\n".join(
            f"[{issue.code}] {issue.message}"
            for issue in self.errors
        )

        raise ScoringValidationError(
            "CMMC scoring validation failed:\n"
            f"{details}"
        )


class ScoringValidator:
    """
    Validate the generated CMMC scoring table.

    This validator checks:

    - exactly 110 unique requirements;
    - required CSV fields;
    - valid 1-, 3-, and 5-point values;
    - expected scoring-category counts;
    - partial-credit configuration;
    - domain-to-requirement consistency;
    - total possible deduction;
    - mathematical minimum score;
    - agreement with scoring compiler constants.

    This confirms internal consistency. It does not independently prove
    that the regulatory mapping encoded in scoring_compiler.py is correct.
    """

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

    EXPECTED_CATEGORY_COUNTS = {
        "ONE_POINT": EXPECTED_ONE_POINT_COUNT,
        "THREE_POINT": EXPECTED_THREE_POINT_COUNT,
        "FIVE_POINT": EXPECTED_FIVE_POINT_COUNT,
        "PARTIAL_3_OR_5": EXPECTED_PARTIAL_CREDIT_COUNT,
    }

    def validate_csv(
        self,
        scoring_weights_csv: Path,
    ) -> ScoringValidationReport:
        rows = self._read_csv(scoring_weights_csv)
        rules = self._rows_to_rules(rows)

        return self.validate_rules(rules)

    def validate_csv_or_raise(
        self,
        scoring_weights_csv: Path,
    ) -> ScoringValidationReport:
        report = self.validate_csv(scoring_weights_csv)
        report.raise_for_errors()
        return report

    def validate_rules(
        self,
        rules: Sequence[ScoringRule],
    ) -> ScoringValidationReport:
        category_counts = dict(
            Counter(
                rule.scoring_category
                for rule in rules
            )
        )

        total_possible_deduction = sum(
            rule.full_deduction_points
            for rule in rules
        )

        minimum_score = (
            MAXIMUM_SCORE
            - total_possible_deduction
        )

        report = ScoringValidationReport(
            rule_count=len(rules),
            category_counts=category_counts,
            total_possible_deduction=(
                total_possible_deduction
            ),
            minimum_score=minimum_score,
        )

        self._validate_rule_count(
            rules,
            report,
        )
        self._validate_unique_ids(
            rules,
            report,
        )
        self._validate_category_counts(
            category_counts,
            report,
        )
        self._validate_rules(
            rules,
            report,
        )
        self._validate_explicit_mapping(
            rules,
            report,
        )
        self._validate_totals(
            report,
        )

        return report

    def validate_rules_or_raise(
        self,
        rules: Sequence[ScoringRule],
    ) -> ScoringValidationReport:
        report = self.validate_rules(rules)
        report.raise_for_errors()
        return report

    def _read_csv(
        self,
        path: Path,
    ) -> List[dict[str, str]]:
        if not path.exists():
            raise FileNotFoundError(
                f"Scoring weights CSV was not found: {path}"
            )

        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            if reader.fieldnames is None:
                raise ScoringValidationError(
                    "Scoring weights CSV has no header."
                )

            missing_columns = (
                self.REQUIRED_COLUMNS
                - set(reader.fieldnames)
            )

            if missing_columns:
                raise ScoringValidationError(
                    "Scoring weights CSV is missing columns: "
                    + ", ".join(
                        sorted(missing_columns)
                    )
                )

            return list(reader)

    def _rows_to_rules(
        self,
        rows: Sequence[dict[str, str]],
    ) -> List[ScoringRule]:
        rules: List[ScoringRule] = []

        for row_number, row in enumerate(
            rows,
            start=2,
        ):
            try:
                rule = ScoringRule(
                    requirement_id=(
                        self._normalize_requirement_id(
                            row["requirement_id"]
                        )
                    ),
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
                    deduction_points=int(
                        row["deduction_points"]
                    ),
                    partial_credit_allowed=(
                        self._parse_bool(
                            row[
                                "partial_credit_allowed"
                            ]
                        )
                    ),
                    partial_deduction_points=int(
                        row[
                            "partial_deduction_points"
                        ]
                    ),
                    full_deduction_points=int(
                        row[
                            "full_deduction_points"
                        ]
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
            except (
                KeyError,
                TypeError,
                ValueError,
            ) as error:
                raise ScoringValidationError(
                    "Unable to parse scoring row "
                    f"{row_number}: {error}"
                ) from error

            rules.append(rule)

        return rules

    def _validate_rule_count(
        self,
        rules: Sequence[ScoringRule],
        report: ScoringValidationReport,
    ) -> None:
        if len(rules) != EXPECTED_REQUIREMENT_COUNT:
            self._add_error(
                report,
                code="RULE_COUNT",
                message=(
                    f"Expected {EXPECTED_REQUIREMENT_COUNT} "
                    f"scoring rules, but found {len(rules)}."
                ),
            )

    def _validate_unique_ids(
        self,
        rules: Sequence[ScoringRule],
        report: ScoringValidationReport,
    ) -> None:
        counts = Counter(
            rule.requirement_id
            for rule in rules
        )

        for requirement_id, count in counts.items():
            if count > 1:
                self._add_error(
                    report,
                    code="DUPLICATE_REQUIREMENT",
                    message=(
                        f"Requirement {requirement_id} "
                        f"appears {count} times."
                    ),
                    requirement_id=requirement_id,
                )

    def _validate_category_counts(
        self,
        category_counts: Dict[str, int],
        report: ScoringValidationReport,
    ) -> None:
        unexpected_categories = (
            set(category_counts)
            - self.VALID_CATEGORIES
        )

        for category in sorted(
            unexpected_categories
        ):
            self._add_error(
                report,
                code="INVALID_CATEGORY",
                message=(
                    f"Unsupported scoring category: "
                    f"{category}."
                ),
            )

        for category, expected_count in (
            self.EXPECTED_CATEGORY_COUNTS.items()
        ):
            actual_count = category_counts.get(
                category,
                0,
            )

            if actual_count != expected_count:
                self._add_error(
                    report,
                    code="CATEGORY_COUNT",
                    message=(
                        f"Category {category} expected "
                        f"{expected_count} rows, but found "
                        f"{actual_count}."
                    ),
                )

    def _validate_rules(
        self,
        rules: Sequence[ScoringRule],
        report: ScoringValidationReport,
    ) -> None:
        for rule in rules:
            self._validate_rule(
                rule,
                report,
            )

    def _validate_rule(
        self,
        rule: ScoringRule,
        report: ScoringValidationReport,
    ) -> None:
        requirement_id = rule.requirement_id

        if not requirement_id:
            self._add_error(
                report,
                code="EMPTY_REQUIREMENT_ID",
                message="A scoring rule has an empty ID.",
            )
            return

        expected_domain = requirement_id[:2]

        if rule.domain_code != expected_domain:
            self._add_error(
                report,
                code="DOMAIN_MISMATCH",
                message=(
                    f"{requirement_id} has domain "
                    f"{rule.domain_code}; expected "
                    f"{expected_domain}."
                ),
                requirement_id=requirement_id,
            )

        if rule.scoring_category not in (
            self.VALID_CATEGORIES
        ):
            self._add_error(
                report,
                code="INVALID_CATEGORY",
                message=(
                    f"{requirement_id} has unsupported "
                    f"category "
                    f"{rule.scoring_category}."
                ),
                requirement_id=requirement_id,
            )

        if rule.deduction_points not in {
            1,
            3,
            5,
        }:
            self._add_error(
                report,
                code="INVALID_DEDUCTION",
                message=(
                    f"{requirement_id} has deduction "
                    f"{rule.deduction_points}; expected "
                    "1, 3, or 5."
                ),
                requirement_id=requirement_id,
            )

        if rule.full_deduction_points not in {
            1,
            3,
            5,
        }:
            self._add_error(
                report,
                code="INVALID_FULL_DEDUCTION",
                message=(
                    f"{requirement_id} has invalid full "
                    f"deduction "
                    f"{rule.full_deduction_points}."
                ),
                requirement_id=requirement_id,
            )

        if rule.partial_credit_allowed:
            if rule.scoring_category != (
                "PARTIAL_3_OR_5"
            ):
                self._add_error(
                    report,
                    code="PARTIAL_CATEGORY_MISMATCH",
                    message=(
                        f"{requirement_id} permits partial "
                        "credit but is not categorized as "
                        "PARTIAL_3_OR_5."
                    ),
                    requirement_id=requirement_id,
                )

            if (
                rule.partial_deduction_points != 3
                or rule.full_deduction_points != 5
            ):
                self._add_error(
                    report,
                    code="INVALID_PARTIAL_RULE",
                    message=(
                        f"{requirement_id} must use a "
                        "3-point partial and 5-point full "
                        "deduction."
                    ),
                    requirement_id=requirement_id,
                )

            if not rule.partial_credit_condition:
                self._add_error(
                    report,
                    code="EMPTY_PARTIAL_CONDITION",
                    message=(
                        f"{requirement_id} allows partial "
                        "credit but has no condition text."
                    ),
                    requirement_id=requirement_id,
                )

        else:
            if rule.partial_deduction_points != 0:
                self._add_error(
                    report,
                    code="UNEXPECTED_PARTIAL_VALUE",
                    message=(
                        f"{requirement_id} does not permit "
                        "partial credit but has partial "
                        f"deduction "
                        f"{rule.partial_deduction_points}."
                    ),
                    requirement_id=requirement_id,
                )

            if rule.scoring_category == (
                "PARTIAL_3_OR_5"
            ):
                self._add_error(
                    report,
                    code="MISSING_PARTIAL_FLAG",
                    message=(
                        f"{requirement_id} is categorized "
                        "as PARTIAL_3_OR_5 but partial credit "
                        "is disabled."
                    ),
                    requirement_id=requirement_id,
                )

        expected_points = {
            "ONE_POINT": 1,
            "THREE_POINT": 3,
            "FIVE_POINT": 5,
            "PARTIAL_3_OR_5": 5,
        }.get(rule.scoring_category)

        if (
            expected_points is not None
            and rule.full_deduction_points
            != expected_points
        ):
            self._add_error(
                report,
                code="CATEGORY_POINT_MISMATCH",
                message=(
                    f"{requirement_id} category "
                    f"{rule.scoring_category} requires "
                    f"{expected_points} full deduction "
                    f"points, but has "
                    f"{rule.full_deduction_points}."
                ),
                requirement_id=requirement_id,
            )

        if not rule.scoring_source:
            self._add_warning(
                report,
                code="MISSING_SOURCE",
                message=(
                    f"{requirement_id} has no scoring "
                    "source reference."
                ),
                requirement_id=requirement_id,
            )

        if not rule.scoring_source_version:
            self._add_warning(
                report,
                code="MISSING_SOURCE_VERSION",
                message=(
                    f"{requirement_id} has no scoring "
                    "source version."
                ),
                requirement_id=requirement_id,
            )

    def _validate_explicit_mapping(
        self,
        rules: Sequence[ScoringRule],
        report: ScoringValidationReport,
    ) -> None:
        rule_map = {
            rule.requirement_id: rule
            for rule in rules
        }

        for requirement_id in (
            FIVE_POINT_REQUIREMENTS
        ):
            rule = rule_map.get(requirement_id)

            if rule is None:
                self._add_error(
                    report,
                    code="MISSING_FIVE_POINT_RULE",
                    message=(
                        f"Five-point requirement "
                        f"{requirement_id} is missing."
                    ),
                    requirement_id=requirement_id,
                )
                continue

            if rule.scoring_category != "FIVE_POINT":
                self._add_error(
                    report,
                    code="FIVE_POINT_MAPPING",
                    message=(
                        f"{requirement_id} should be "
                        "FIVE_POINT but is "
                        f"{rule.scoring_category}."
                    ),
                    requirement_id=requirement_id,
                )

        for requirement_id in (
            THREE_POINT_REQUIREMENTS
        ):
            rule = rule_map.get(requirement_id)

            if rule is None:
                self._add_error(
                    report,
                    code="MISSING_THREE_POINT_RULE",
                    message=(
                        f"Three-point requirement "
                        f"{requirement_id} is missing."
                    ),
                    requirement_id=requirement_id,
                )
                continue

            if rule.scoring_category != (
                "THREE_POINT"
            ):
                self._add_error(
                    report,
                    code="THREE_POINT_MAPPING",
                    message=(
                        f"{requirement_id} should be "
                        "THREE_POINT but is "
                        f"{rule.scoring_category}."
                    ),
                    requirement_id=requirement_id,
                )

        for requirement_id in (
            PARTIAL_CREDIT_REQUIREMENTS
        ):
            rule = rule_map.get(requirement_id)

            if rule is None:
                self._add_error(
                    report,
                    code="MISSING_PARTIAL_RULE",
                    message=(
                        f"Partial-credit requirement "
                        f"{requirement_id} is missing."
                    ),
                    requirement_id=requirement_id,
                )
                continue

            if (
                rule.scoring_category
                != "PARTIAL_3_OR_5"
                or not rule.partial_credit_allowed
            ):
                self._add_error(
                    report,
                    code="PARTIAL_MAPPING",
                    message=(
                        f"{requirement_id} does not have "
                        "the expected partial-credit "
                        "configuration."
                    ),
                    requirement_id=requirement_id,
                )

    def _validate_totals(
        self,
        report: ScoringValidationReport,
    ) -> None:
        if (
            report.total_possible_deduction
            != EXPECTED_MAXIMUM_DEDUCTION
        ):
            self._add_error(
                report,
                code="TOTAL_DEDUCTION",
                message=(
                    "Expected total possible deduction of "
                    f"{EXPECTED_MAXIMUM_DEDUCTION}, but "
                    f"calculated "
                    f"{report.total_possible_deduction}."
                ),
            )

        if (
            report.minimum_score
            != EXPECTED_MINIMUM_SCORE
        ):
            self._add_error(
                report,
                code="MINIMUM_SCORE",
                message=(
                    f"Expected minimum score of "
                    f"{EXPECTED_MINIMUM_SCORE}, but "
                    f"calculated "
                    f"{report.minimum_score}."
                ),
            )

    @staticmethod
    def _add_error(
        report: ScoringValidationReport,
        code: str,
        message: str,
        requirement_id: str = "",
    ) -> None:
        report.errors.append(
            ScoringValidationIssue(
                severity="ERROR",
                code=code,
                message=message,
                requirement_id=requirement_id,
            )
        )

    @staticmethod
    def _add_warning(
        report: ScoringValidationReport,
        code: str,
        message: str,
        requirement_id: str = "",
    ) -> None:
        report.warnings.append(
            ScoringValidationIssue(
                severity="WARNING",
                code=code,
                message=message,
                requirement_id=requirement_id,
            )
        )

    @staticmethod
    def _parse_bool(
        value: str,
    ) -> bool:
        normalized = value.strip().lower()

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

        raise ScoringValidationError(
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