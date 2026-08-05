from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

from src.compiler.content_parser import ParsedRequirement


EXPECTED_REQUIREMENT_COUNT = 110

EXPECTED_DOMAIN_COUNTS: Dict[str, int] = {
    "AC": 22,
    "AT": 3,
    "AU": 9,
    "CM": 9,
    "IA": 11,
    "IR": 3,
    "MA": 6,
    "MP": 9,
    "PS": 2,
    "PE": 6,
    "RA": 3,
    "CA": 4,
    "SC": 16,
    "SI": 7,
}

EXPECTED_FIRST_REQUIREMENT = "AC.L2-3.1.1"
EXPECTED_LAST_REQUIREMENT = "SI.L2-3.14.7"


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    requirement_id: str = ""


@dataclass
class ValidationReport:
    requirement_count: int
    domain_counts: Dict[str, int]
    errors: List[ValidationIssue] = field(
        default_factory=list
    )
    warnings: List[ValidationIssue] = field(
        default_factory=list
    )

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def raise_for_errors(self) -> None:
        if self.passed:
            return

        messages = [
            f"[{issue.code}] {issue.message}"
            for issue in self.errors
        ]

        raise ValidationError(
            "CMMC compiler validation failed:\n"
            + "\n".join(messages)
        )


class ValidationError(RuntimeError):
    """Raised when compiled CMMC data fails validation."""


class RequirementValidator:
    """
    Validate normalized CMMC Level 2 requirements before export.

    Errors prevent export. Warnings identify incomplete optional or
    supporting data that should be reviewed.
    """

    def validate(
        self,
        requirements: Sequence[ParsedRequirement],
    ) -> ValidationReport:
        domain_counts = dict(
            Counter(
                requirement.domain_code
                for requirement in requirements
            )
        )

        report = ValidationReport(
            requirement_count=len(requirements),
            domain_counts=domain_counts,
        )

        self._validate_requirement_count(
            requirements,
            report,
        )
        self._validate_domain_counts(
            domain_counts,
            report,
        )
        self._validate_requirement_order(
            requirements,
            report,
        )
        self._validate_unique_requirement_ids(
            requirements,
            report,
        )
        self._validate_requirements(
            requirements,
            report,
        )

        return report

    def validate_or_raise(
        self,
        requirements: Sequence[ParsedRequirement],
    ) -> ValidationReport:
        report = self.validate(requirements)
        report.raise_for_errors()
        return report

    @staticmethod
    def _add_error(
        report: ValidationReport,
        code: str,
        message: str,
        requirement_id: str = "",
    ) -> None:
        report.errors.append(
            ValidationIssue(
                severity="ERROR",
                code=code,
                message=message,
                requirement_id=requirement_id,
            )
        )

    @staticmethod
    def _add_warning(
        report: ValidationReport,
        code: str,
        message: str,
        requirement_id: str = "",
    ) -> None:
        report.warnings.append(
            ValidationIssue(
                severity="WARNING",
                code=code,
                message=message,
                requirement_id=requirement_id,
            )
        )

    def _validate_requirement_count(
        self,
        requirements: Sequence[ParsedRequirement],
        report: ValidationReport,
    ) -> None:
        actual_count = len(requirements)

        if actual_count != EXPECTED_REQUIREMENT_COUNT:
            self._add_error(
                report,
                code="REQUIREMENT_COUNT",
                message=(
                    "Expected "
                    f"{EXPECTED_REQUIREMENT_COUNT} requirements, "
                    f"but found {actual_count}."
                ),
            )

    def _validate_domain_counts(
        self,
        actual_counts: Dict[str, int],
        report: ValidationReport,
    ) -> None:
        expected_domains = set(
            EXPECTED_DOMAIN_COUNTS
        )
        actual_domains = set(actual_counts)

        missing_domains = sorted(
            expected_domains - actual_domains
        )
        unexpected_domains = sorted(
            actual_domains - expected_domains
        )

        for domain_code in missing_domains:
            self._add_error(
                report,
                code="MISSING_DOMAIN",
                message=(
                    f"Expected domain {domain_code}, "
                    "but it was not found."
                ),
            )

        for domain_code in unexpected_domains:
            self._add_error(
                report,
                code="UNEXPECTED_DOMAIN",
                message=(
                    f"Unexpected domain found: {domain_code}."
                ),
            )

        for domain_code, expected_count in (
            EXPECTED_DOMAIN_COUNTS.items()
        ):
            actual_count = actual_counts.get(
                domain_code,
                0,
            )

            if actual_count != expected_count:
                self._add_error(
                    report,
                    code="DOMAIN_COUNT",
                    message=(
                        f"Domain {domain_code} expected "
                        f"{expected_count} requirements, "
                        f"but found {actual_count}."
                    ),
                )

    def _validate_requirement_order(
        self,
        requirements: Sequence[ParsedRequirement],
        report: ValidationReport,
    ) -> None:
        if not requirements:
            self._add_error(
                report,
                code="EMPTY_REQUIREMENTS",
                message="No requirements were supplied.",
            )
            return

        first_id = requirements[0].requirement_id
        last_id = requirements[-1].requirement_id

        if first_id != EXPECTED_FIRST_REQUIREMENT:
            self._add_error(
                report,
                code="FIRST_REQUIREMENT",
                message=(
                    "Expected the first requirement to be "
                    f"{EXPECTED_FIRST_REQUIREMENT}, "
                    f"but found {first_id}."
                ),
                requirement_id=first_id,
            )

        if last_id != EXPECTED_LAST_REQUIREMENT:
            self._add_error(
                report,
                code="LAST_REQUIREMENT",
                message=(
                    "Expected the last requirement to be "
                    f"{EXPECTED_LAST_REQUIREMENT}, "
                    f"but found {last_id}."
                ),
                requirement_id=last_id,
            )

    def _validate_unique_requirement_ids(
        self,
        requirements: Sequence[ParsedRequirement],
        report: ValidationReport,
    ) -> None:
        counts = Counter(
            requirement.requirement_id
            for requirement in requirements
        )

        duplicate_ids = sorted(
            requirement_id
            for requirement_id, count in counts.items()
            if count > 1
        )

        for requirement_id in duplicate_ids:
            self._add_error(
                report,
                code="DUPLICATE_REQUIREMENT_ID",
                message=(
                    "Duplicate requirement ID found: "
                    f"{requirement_id}."
                ),
                requirement_id=requirement_id,
            )

    def _validate_requirements(
        self,
        requirements: Sequence[ParsedRequirement],
        report: ValidationReport,
    ) -> None:
        for requirement in requirements:
            self._validate_requirement(
                requirement,
                report,
            )

    def _validate_requirement(
        self,
        requirement: ParsedRequirement,
        report: ValidationReport,
    ) -> None:
        requirement_id = requirement.requirement_id

        if not requirement_id.strip():
            self._add_error(
                report,
                code="EMPTY_REQUIREMENT_ID",
                message="A requirement has an empty ID.",
            )

        expected_domain = requirement_id[:2]

        if requirement.domain_code != expected_domain:
            self._add_error(
                report,
                code="DOMAIN_ID_MISMATCH",
                message=(
                    f"Requirement {requirement_id} has domain "
                    f"{requirement.domain_code}, but its ID "
                    f"indicates {expected_domain}."
                ),
                requirement_id=requirement_id,
            )

        if not requirement.title.strip():
            self._add_error(
                report,
                code="EMPTY_TITLE",
                message=(
                    f"Requirement {requirement_id} "
                    "has an empty title."
                ),
                requirement_id=requirement_id,
            )

        if not requirement.statement.strip():
            self._add_error(
                report,
                code="EMPTY_STATEMENT",
                message=(
                    f"Requirement {requirement_id} "
                    "has an empty statement."
                ),
                requirement_id=requirement_id,
            )

        if not requirement.objectives:
            self._add_error(
                report,
                code="MISSING_OBJECTIVES",
                message=(
                    f"Requirement {requirement_id} "
                    "has no assessment objectives."
                ),
                requirement_id=requirement_id,
            )
        else:
            self._validate_objectives(
                requirement,
                report,
            )

        if requirement.source_page_start <= 0:
            self._add_error(
                report,
                code="INVALID_START_PAGE",
                message=(
                    f"Requirement {requirement_id} has invalid "
                    f"start page "
                    f"{requirement.source_page_start}."
                ),
                requirement_id=requirement_id,
            )

        if (
            requirement.source_page_end
            < requirement.source_page_start
        ):
            self._add_error(
                report,
                code="INVALID_PAGE_RANGE",
                message=(
                    f"Requirement {requirement_id} has page "
                    f"range {requirement.source_page_start}-"
                    f"{requirement.source_page_end}."
                ),
                requirement_id=requirement_id,
            )

        if not requirement.examine_objects:
            self._add_warning(
                report,
                code="MISSING_EXAMINE_OBJECTS",
                message=(
                    f"Requirement {requirement_id} has no "
                    "parsed Examine objects."
                ),
                requirement_id=requirement_id,
            )

        if not requirement.interview_objects:
            self._add_warning(
                report,
                code="MISSING_INTERVIEW_OBJECTS",
                message=(
                    f"Requirement {requirement_id} has no "
                    "parsed Interview objects."
                ),
                requirement_id=requirement_id,
            )

        if not requirement.test_objects:
            self._add_warning(
                report,
                code="MISSING_TEST_OBJECTS",
                message=(
                    f"Requirement {requirement_id} has no "
                    "parsed Test objects."
                ),
                requirement_id=requirement_id,
            )

        if not requirement.key_references:
            self._add_warning(
                report,
                code="MISSING_KEY_REFERENCES",
                message=(
                    f"Requirement {requirement_id} has no "
                    "parsed key references."
                ),
                requirement_id=requirement_id,
            )

    def _validate_objectives(
        self,
        requirement: ParsedRequirement,
        report: ValidationReport,
    ) -> None:
        objective_ids = [
            objective.objective_id
            for objective in requirement.objectives
        ]

        objective_counts = Counter(objective_ids)

        duplicate_objective_ids = sorted(
            objective_id
            for objective_id, count in (
                objective_counts.items()
            )
            if count > 1
        )

        for objective_id in duplicate_objective_ids:
            self._add_error(
                report,
                code="DUPLICATE_OBJECTIVE_ID",
                message=(
                    f"Requirement "
                    f"{requirement.requirement_id} has "
                    f"duplicate objective {objective_id}."
                ),
                requirement_id=(
                    requirement.requirement_id
                ),
            )

        for objective in requirement.objectives:
            if not objective.objective_id.strip():
                self._add_error(
                    report,
                    code="EMPTY_OBJECTIVE_ID",
                    message=(
                        f"Requirement "
                        f"{requirement.requirement_id} "
                        "contains an objective with no ID."
                    ),
                    requirement_id=(
                        requirement.requirement_id
                    ),
                )

            if not objective.objective_text.strip():
                self._add_error(
                    report,
                    code="EMPTY_OBJECTIVE_TEXT",
                    message=(
                        f"Requirement "
                        f"{requirement.requirement_id}, "
                        f"objective "
                        f"{objective.objective_id}, "
                        "has no text."
                    ),
                    requirement_id=(
                        requirement.requirement_id
                    ),
                )

            if (
                objective.requirement_id
                != requirement.requirement_id
            ):
                self._add_error(
                    report,
                    code="OBJECTIVE_REQUIREMENT_MISMATCH",
                    message=(
                        f"Objective "
                        f"{objective.objective_id} is mapped "
                        f"to {objective.requirement_id}, "
                        f"but is contained under "
                        f"{requirement.requirement_id}."
                    ),
                    requirement_id=(
                        requirement.requirement_id
                    ),
                )