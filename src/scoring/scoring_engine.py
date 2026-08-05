from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

from src.scoring.partial_credit import (
    AssessmentFinding,
    PartialCreditEvaluator,
    PartialCreditResult,
    PartialImplementationState,
)


MAXIMUM_SCORE = 110


class ScoringEngineError(ValueError):
    """Raised when scoring input or scoring configuration is invalid."""


@dataclass(frozen=True)
class ScoringRule:
    """Scoring metadata loaded from scoring_weights.csv."""

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


@dataclass(frozen=True)
class RequirementAssessment:
    """Assessment input for one CMMC Level 2 requirement."""

    requirement_id: str
    finding: AssessmentFinding
    implementation_state: PartialImplementationState | None = None
    applicable: bool = True
    notes: str = ""


@dataclass(frozen=True)
class RequirementScore:
    """Calculated score result for one requirement."""

    requirement_id: str
    domain_code: str
    finding: AssessmentFinding
    implementation_state: PartialImplementationState | None
    deduction_points: int
    maximum_deduction_points: int
    partial_credit_applied: bool
    applicable: bool
    assessed: bool
    explanation: str


@dataclass(frozen=True)
class DomainScore:
    """Summary of scoring results for one domain."""

    domain_code: str
    requirement_count: int
    assessed_count: int
    met_count: int
    not_met_count: int
    not_applicable_count: int
    not_assessed_count: int
    deduction_points: int
    maximum_deduction_points: int

    @property
    def completion_percentage(self) -> float:
        if self.requirement_count == 0:
            return 0.0

        completed = (
            self.met_count
            + self.not_met_count
            + self.not_applicable_count
        )

        return completed / self.requirement_count


@dataclass(frozen=True)
class AssessmentScore:
    """Complete CMMC Level 2 scoring result."""

    maximum_score: int
    current_score: int
    total_deduction_points: int
    maximum_possible_deduction: int
    mathematical_minimum_score: int
    requirement_count: int
    assessed_count: int
    met_count: int
    not_met_count: int
    not_applicable_count: int
    not_assessed_count: int
    partial_credit_count: int
    complete: bool
    requirement_scores: Sequence[RequirementScore]
    domain_scores: Mapping[str, DomainScore]

    @property
    def completion_percentage(self) -> float:
        if self.requirement_count == 0:
            return 0.0

        return self.assessed_count / self.requirement_count


class ScoringEngine:
    """
    Calculate CMMC Level 2 scores from a validated scoring table.

    The engine:

    - loads all 110 scoring rules;
    - calculates 1-, 3-, and 5-point deductions;
    - applies the two permitted partial-credit rules;
    - reports requirement-level and domain-level results;
    - treats NOT ASSESSED requirements as pending, with no current deduction;
    - marks the overall result incomplete until every requirement has a
      final finding.
    """

    def __init__(
        self,
        scoring_weights_csv: Path,
    ) -> None:
        self.scoring_weights_csv = scoring_weights_csv.resolve()
        self.partial_credit_evaluator = PartialCreditEvaluator()
        self.rules = self._load_rules()

    def calculate(
        self,
        assessments: Iterable[RequirementAssessment],
        *,
        require_all_requirements: bool = True,
    ) -> AssessmentScore:
        """
        Calculate the current assessment score.

        Args:
            assessments:
                Assessment inputs. Each requirement may appear only once.

            require_all_requirements:
                When True, all requirements from the scoring table must be
                present in the supplied assessment collection. Missing
                requirements raise ScoringEngineError.

        Returns:
            AssessmentScore containing requirement and domain summaries.
        """

        assessment_map = self._build_assessment_map(
            assessments
        )

        if require_all_requirements:
            self._validate_all_requirements_present(
                assessment_map
            )

        requirement_scores: List[RequirementScore] = []

        for requirement_id, rule in self.rules.items():
            assessment = assessment_map.get(
                requirement_id,
                RequirementAssessment(
                    requirement_id=requirement_id,
                    finding=AssessmentFinding.NOT_ASSESSED,
                    implementation_state=(
                        PartialImplementationState.NOT_ASSESSED
                        if rule.partial_credit_allowed
                        else None
                    ),
                ),
            )

            result = self.score_requirement(
                assessment
            )

            requirement_scores.append(result)

        total_deduction = sum(
            result.deduction_points
            for result in requirement_scores
        )

        current_score = (
            MAXIMUM_SCORE
            - total_deduction
        )

        maximum_possible_deduction = sum(
            rule.full_deduction_points
            for rule in self.rules.values()
        )

        mathematical_minimum_score = (
            MAXIMUM_SCORE
            - maximum_possible_deduction
        )

        met_count = sum(
            result.finding == AssessmentFinding.MET
            for result in requirement_scores
        )

        not_met_count = sum(
            result.finding == AssessmentFinding.NOT_MET
            for result in requirement_scores
        )

        not_applicable_count = sum(
            result.finding
            == AssessmentFinding.NOT_APPLICABLE
            for result in requirement_scores
        )

        not_assessed_count = sum(
            result.finding
            == AssessmentFinding.NOT_ASSESSED
            for result in requirement_scores
        )

        assessed_count = (
            len(requirement_scores)
            - not_assessed_count
        )

        partial_credit_count = sum(
            result.partial_credit_applied
            for result in requirement_scores
        )

        domain_scores = self._build_domain_scores(
            requirement_scores
        )

        return AssessmentScore(
            maximum_score=MAXIMUM_SCORE,
            current_score=current_score,
            total_deduction_points=total_deduction,
            maximum_possible_deduction=(
                maximum_possible_deduction
            ),
            mathematical_minimum_score=(
                mathematical_minimum_score
            ),
            requirement_count=len(
                requirement_scores
            ),
            assessed_count=assessed_count,
            met_count=met_count,
            not_met_count=not_met_count,
            not_applicable_count=(
                not_applicable_count
            ),
            not_assessed_count=(
                not_assessed_count
            ),
            partial_credit_count=(
                partial_credit_count
            ),
            complete=not_assessed_count == 0,
            requirement_scores=tuple(
                requirement_scores
            ),
            domain_scores=domain_scores,
        )

    def score_requirement(
        self,
        assessment: RequirementAssessment,
    ) -> RequirementScore:
        """Calculate the deduction for one requirement."""

        requirement_id = self._normalize_requirement_id(
            assessment.requirement_id
        )

        try:
            rule = self.rules[requirement_id]
        except KeyError as error:
            raise ScoringEngineError(
                "No scoring rule exists for requirement "
                f"{requirement_id}."
            ) from error

        finding = self._coerce_finding(
            assessment.finding
        )

        applicable = assessment.applicable

        if not applicable:
            if finding not in {
                AssessmentFinding.NOT_APPLICABLE,
                AssessmentFinding.NOT_ASSESSED,
            }:
                raise ScoringEngineError(
                    f"{requirement_id} is marked non-applicable "
                    f"but has finding {finding.value}."
                )

        if finding == AssessmentFinding.NOT_APPLICABLE:
            return RequirementScore(
                requirement_id=requirement_id,
                domain_code=rule.domain_code,
                finding=finding,
                implementation_state=(
                    assessment.implementation_state
                ),
                deduction_points=0,
                maximum_deduction_points=(
                    rule.full_deduction_points
                ),
                partial_credit_applied=False,
                applicable=False,
                assessed=True,
                explanation=(
                    f"{requirement_id} is assessed "
                    "NOT APPLICABLE; no deduction is applied."
                ),
            )

        if finding == AssessmentFinding.NOT_ASSESSED:
            return RequirementScore(
                requirement_id=requirement_id,
                domain_code=rule.domain_code,
                finding=finding,
                implementation_state=(
                    assessment.implementation_state
                ),
                deduction_points=0,
                maximum_deduction_points=(
                    rule.full_deduction_points
                ),
                partial_credit_applied=False,
                applicable=applicable,
                assessed=False,
                explanation=(
                    f"{requirement_id} has not been assessed; "
                    "its deduction remains pending."
                ),
            )

        if finding == AssessmentFinding.MET:
            if (
                rule.partial_credit_allowed
                and assessment.implementation_state
                not in {
                    None,
                    PartialImplementationState.FULLY_IMPLEMENTED,
                }
            ):
                raise ScoringEngineError(
                    f"{requirement_id} assessed MET must be "
                    "FULLY IMPLEMENTED."
                )

            return RequirementScore(
                requirement_id=requirement_id,
                domain_code=rule.domain_code,
                finding=finding,
                implementation_state=(
                    assessment.implementation_state
                ),
                deduction_points=0,
                maximum_deduction_points=(
                    rule.full_deduction_points
                ),
                partial_credit_applied=False,
                applicable=applicable,
                assessed=True,
                explanation=(
                    f"{requirement_id} is assessed MET; "
                    "no points are deducted."
                ),
            )

        if finding != AssessmentFinding.NOT_MET:
            raise ScoringEngineError(
                f"Unsupported finding for {requirement_id}: "
                f"{finding.value}."
            )

        if rule.partial_credit_allowed:
            implementation_state = (
                assessment.implementation_state
            )

            if implementation_state is None:
                raise ScoringEngineError(
                    f"{requirement_id} requires an "
                    "implementation state when assessed NOT MET."
                )

            partial_result = (
                self.partial_credit_evaluator.evaluate(
                    requirement_id=requirement_id,
                    finding=finding,
                    implementation_state=(
                        implementation_state
                    ),
                )
            )

            return self._from_partial_credit_result(
                rule=rule,
                result=partial_result,
                applicable=applicable,
            )

        if assessment.implementation_state not in {
            None,
            PartialImplementationState.NOT_IMPLEMENTED,
        }:
            raise ScoringEngineError(
                f"{requirement_id} does not permit partial "
                "credit or a partial implementation state."
            )

        return RequirementScore(
            requirement_id=requirement_id,
            domain_code=rule.domain_code,
            finding=finding,
            implementation_state=(
                assessment.implementation_state
            ),
            deduction_points=(
                rule.full_deduction_points
            ),
            maximum_deduction_points=(
                rule.full_deduction_points
            ),
            partial_credit_applied=False,
            applicable=applicable,
            assessed=True,
            explanation=(
                f"{requirement_id} is assessed NOT MET; "
                f"{rule.full_deduction_points} points are "
                "deducted."
            ),
        )

    def create_default_assessments(
        self,
    ) -> List[RequirementAssessment]:
        """Create one NOT ASSESSED input for every scoring rule."""

        defaults: List[RequirementAssessment] = []

        for rule in self.rules.values():
            defaults.append(
                RequirementAssessment(
                    requirement_id=rule.requirement_id,
                    finding=(
                        AssessmentFinding.NOT_ASSESSED
                    ),
                    implementation_state=(
                        PartialImplementationState.NOT_ASSESSED
                        if rule.partial_credit_allowed
                        else None
                    ),
                )
            )

        return defaults

    def get_rule(
        self,
        requirement_id: str,
    ) -> ScoringRule:
        """Return the scoring rule for one requirement."""

        normalized_id = self._normalize_requirement_id(
            requirement_id
        )

        try:
            return self.rules[normalized_id]
        except KeyError as error:
            raise ScoringEngineError(
                f"No scoring rule exists for {normalized_id}."
            ) from error

    def _load_rules(
        self,
    ) -> Dict[str, ScoringRule]:
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

            required_columns = {
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

            if reader.fieldnames is None:
                raise ScoringEngineError(
                    "Scoring weights CSV has no header."
                )

            missing_columns = (
                required_columns
                - set(reader.fieldnames)
            )

            if missing_columns:
                raise ScoringEngineError(
                    "Scoring weights CSV is missing columns: "
                    + ", ".join(
                        sorted(missing_columns)
                    )
                )

            rows = list(reader)

        if len(rows) != 110:
            raise ScoringEngineError(
                "Expected 110 scoring rules, "
                f"but found {len(rows)}."
            )

        rules: Dict[str, ScoringRule] = {}

        for row in rows:
            requirement_id = (
                self._normalize_requirement_id(
                    row["requirement_id"]
                )
            )

            if requirement_id in rules:
                raise ScoringEngineError(
                    "Duplicate scoring rule found for "
                    f"{requirement_id}."
                )

            rule = ScoringRule(
                requirement_id=requirement_id,
                domain_code=row[
                    "domain_code"
                ].strip().upper(),
                scoring_category=row[
                    "scoring_category"
                ].strip().upper(),
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
                partial_credit_condition=row[
                    "partial_credit_condition"
                ].strip(),
                full_deduction_condition=row[
                    "full_deduction_condition"
                ].strip(),
                scoring_source=row[
                    "scoring_source"
                ].strip(),
                scoring_source_version=row[
                    "scoring_source_version"
                ].strip(),
            )

            self._validate_rule(rule)
            rules[requirement_id] = rule

        return rules

    @staticmethod
    def _validate_rule(
        rule: ScoringRule,
    ) -> None:
        if rule.deduction_points not in {
            1,
            3,
            5,
        }:
            raise ScoringEngineError(
                f"{rule.requirement_id} has invalid "
                f"deduction points "
                f"{rule.deduction_points}."
            )

        if rule.full_deduction_points not in {
            1,
            3,
            5,
        }:
            raise ScoringEngineError(
                f"{rule.requirement_id} has invalid full "
                "deduction points."
            )

        if rule.partial_credit_allowed:
            if (
                rule.partial_deduction_points != 3
                or rule.full_deduction_points != 5
            ):
                raise ScoringEngineError(
                    f"{rule.requirement_id} has an invalid "
                    "partial-credit configuration."
                )

        elif rule.partial_deduction_points != 0:
            raise ScoringEngineError(
                f"{rule.requirement_id} does not allow "
                "partial credit but has a nonzero partial "
                "deduction."
            )

        expected_domain = rule.requirement_id[:2]

        if rule.domain_code != expected_domain:
            raise ScoringEngineError(
                f"{rule.requirement_id} has domain "
                f"{rule.domain_code}, expected "
                f"{expected_domain}."
            )

    def _build_assessment_map(
        self,
        assessments: Iterable[RequirementAssessment],
    ) -> Dict[str, RequirementAssessment]:
        assessment_map: Dict[
            str,
            RequirementAssessment,
        ] = {}

        for assessment in assessments:
            requirement_id = (
                self._normalize_requirement_id(
                    assessment.requirement_id
                )
            )

            if requirement_id in assessment_map:
                raise ScoringEngineError(
                    "Duplicate assessment supplied for "
                    f"{requirement_id}."
                )

            normalized_finding = (
                self._coerce_finding(
                    assessment.finding
                )
            )

            normalized_state = (
                self._coerce_optional_state(
                    assessment.implementation_state
                )
            )

            assessment_map[requirement_id] = (
                RequirementAssessment(
                    requirement_id=requirement_id,
                    finding=normalized_finding,
                    implementation_state=(
                        normalized_state
                    ),
                    applicable=assessment.applicable,
                    notes=assessment.notes,
                )
            )

        unknown_ids = (
            set(assessment_map)
            - set(self.rules)
        )

        if unknown_ids:
            raise ScoringEngineError(
                "Assessments contain unknown requirement IDs: "
                + ", ".join(
                    sorted(unknown_ids)
                )
            )

        return assessment_map

    def _validate_all_requirements_present(
        self,
        assessment_map: Mapping[
            str,
            RequirementAssessment,
        ],
    ) -> None:
        missing_ids = (
            set(self.rules)
            - set(assessment_map)
        )

        if missing_ids:
            raise ScoringEngineError(
                "Assessments are missing requirement IDs: "
                + ", ".join(
                    sorted(missing_ids)
                )
            )

    @staticmethod
    def _from_partial_credit_result(
        rule: ScoringRule,
        result: PartialCreditResult,
        applicable: bool,
    ) -> RequirementScore:
        return RequirementScore(
            requirement_id=result.requirement_id,
            domain_code=rule.domain_code,
            finding=result.finding,
            implementation_state=(
                result.implementation_state
            ),
            deduction_points=(
                result.deduction_points
            ),
            maximum_deduction_points=(
                rule.full_deduction_points
            ),
            partial_credit_applied=(
                result.partial_credit_applied
            ),
            applicable=applicable,
            assessed=True,
            explanation=result.explanation,
        )

    @staticmethod
    def _build_domain_scores(
        requirement_scores: Sequence[
            RequirementScore
        ],
    ) -> Dict[str, DomainScore]:
        grouped: Dict[
            str,
            List[RequirementScore],
        ] = {}

        for result in requirement_scores:
            grouped.setdefault(
                result.domain_code,
                [],
            ).append(result)

        domain_scores: Dict[str, DomainScore] = {}

        for domain_code, results in grouped.items():
            met_count = sum(
                result.finding
                == AssessmentFinding.MET
                for result in results
            )

            not_met_count = sum(
                result.finding
                == AssessmentFinding.NOT_MET
                for result in results
            )

            not_applicable_count = sum(
                result.finding
                == AssessmentFinding.NOT_APPLICABLE
                for result in results
            )

            not_assessed_count = sum(
                result.finding
                == AssessmentFinding.NOT_ASSESSED
                for result in results
            )

            domain_scores[domain_code] = DomainScore(
                domain_code=domain_code,
                requirement_count=len(results),
                assessed_count=(
                    len(results)
                    - not_assessed_count
                ),
                met_count=met_count,
                not_met_count=not_met_count,
                not_applicable_count=(
                    not_applicable_count
                ),
                not_assessed_count=(
                    not_assessed_count
                ),
                deduction_points=sum(
                    result.deduction_points
                    for result in results
                ),
                maximum_deduction_points=sum(
                    result.maximum_deduction_points
                    for result in results
                ),
            )

        return domain_scores

    @staticmethod
    def _coerce_finding(
        value: AssessmentFinding | str,
    ) -> AssessmentFinding:
        if isinstance(
            value,
            AssessmentFinding,
        ):
            return value

        normalized = (
            str(value)
            .strip()
            .upper()
            .replace("_", " ")
        )

        aliases = {
            "MET": AssessmentFinding.MET,
            "NOT MET": (
                AssessmentFinding.NOT_MET
            ),
            "NOT APPLICABLE": (
                AssessmentFinding.NOT_APPLICABLE
            ),
            "N/A": (
                AssessmentFinding.NOT_APPLICABLE
            ),
            "NA": (
                AssessmentFinding.NOT_APPLICABLE
            ),
            "NOT ASSESSED": (
                AssessmentFinding.NOT_ASSESSED
            ),
        }

        try:
            return aliases[normalized]
        except KeyError as error:
            raise ScoringEngineError(
                "Unsupported assessment finding: "
                f"{value}"
            ) from error

    @staticmethod
    def _coerce_optional_state(
        value: (
            PartialImplementationState
            | str
            | None
        ),
    ) -> PartialImplementationState | None:
        if value is None:
            return None

        if isinstance(
            value,
            PartialImplementationState,
        ):
            return value

        normalized = (
            str(value)
            .strip()
            .upper()
            .replace("_", " ")
        )

        aliases = {
            "FULLY IMPLEMENTED": (
                PartialImplementationState.FULLY_IMPLEMENTED
            ),
            "PARTIALLY IMPLEMENTED": (
                PartialImplementationState.PARTIALLY_IMPLEMENTED
            ),
            "PARTIAL": (
                PartialImplementationState.PARTIALLY_IMPLEMENTED
            ),
            "NOT IMPLEMENTED": (
                PartialImplementationState.NOT_IMPLEMENTED
            ),
            "NOT APPLICABLE": (
                PartialImplementationState.NOT_APPLICABLE
            ),
            "N/A": (
                PartialImplementationState.NOT_APPLICABLE
            ),
            "NA": (
                PartialImplementationState.NOT_APPLICABLE
            ),
            "NOT ASSESSED": (
                PartialImplementationState.NOT_ASSESSED
            ),
        }

        try:
            return aliases[normalized]
        except KeyError as error:
            raise ScoringEngineError(
                "Unsupported implementation state: "
                f"{value}"
            ) from error

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

        raise ScoringEngineError(
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