from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict


class AssessmentFinding(str, Enum):
    """
    Permitted CMMC assessment findings.

    Partial implementation does not create a separate assessment finding.
    A partially effective requirement remains NOT MET, but may receive an
    adjusted deduction where 32 CFR 170.24 explicitly permits it.
    """

    MET = "MET"
    NOT_MET = "NOT MET"
    NOT_APPLICABLE = "NOT APPLICABLE"
    NOT_ASSESSED = "NOT ASSESSED"


class PartialImplementationState(str, Enum):
    """
    Implementation states used only for requirements with regulatory
    partial-credit rules.
    """

    NOT_APPLICABLE = "NOT APPLICABLE"
    FULLY_IMPLEMENTED = "FULLY IMPLEMENTED"
    PARTIALLY_IMPLEMENTED = "PARTIALLY IMPLEMENTED"
    NOT_IMPLEMENTED = "NOT IMPLEMENTED"
    NOT_ASSESSED = "NOT ASSESSED"


@dataclass(frozen=True)
class PartialCreditRule:
    """Regulatory partial-credit configuration for one requirement."""

    requirement_id: str
    partial_deduction_points: int
    full_deduction_points: int
    partial_condition: str
    full_deduction_condition: str
    source: str


@dataclass(frozen=True)
class PartialCreditResult:
    """Result of evaluating one requirement for partial credit."""

    requirement_id: str
    finding: AssessmentFinding
    implementation_state: PartialImplementationState
    deduction_points: int
    partial_credit_applied: bool
    explanation: str


PARTIAL_CREDIT_RULES: Dict[str, PartialCreditRule] = {
    "IA.L2-3.5.3": PartialCreditRule(
        requirement_id="IA.L2-3.5.3",
        partial_deduction_points=3,
        full_deduction_points=5,
        partial_condition=(
            "Multi-factor authentication is implemented only for "
            "remote and privileged users."
        ),
        full_deduction_condition=(
            "Multi-factor authentication is not implemented for any users."
        ),
        source="32 CFR 170.24(c)(2)(i)(B)(4)(i)",
    ),
    "SC.L2-3.13.11": PartialCreditRule(
        requirement_id="SC.L2-3.13.11",
        partial_deduction_points=3,
        full_deduction_points=5,
        partial_condition=(
            "Encryption is employed to protect CUI, but the encryption "
            "is not FIPS-validated."
        ),
        full_deduction_condition=(
            "Encryption is not employed to protect CUI."
        ),
        source="32 CFR 170.24(c)(2)(i)(B)(4)(ii)",
    ),
}


class PartialCreditError(ValueError):
    """Raised when partial-credit inputs are invalid or inconsistent."""


class PartialCreditEvaluator:
    """
    Evaluate the two CMMC Level 2 requirements that permit adjusted
    deductions for partially effective implementation.

    IA.L2-3.5.3:
        MET or N/A             -> 0 points deducted
        PARTIALLY IMPLEMENTED  -> 3 points deducted
        NOT IMPLEMENTED        -> 5 points deducted

    SC.L2-3.13.11:
        MET or N/A             -> 0 points deducted
        PARTIALLY IMPLEMENTED  -> 3 points deducted
        NOT IMPLEMENTED        -> 5 points deducted
    """

    def supports(
        self,
        requirement_id: str,
    ) -> bool:
        """Return True when a requirement has a partial-credit rule."""

        return self._normalize_requirement_id(
            requirement_id
        ) in PARTIAL_CREDIT_RULES

    def get_rule(
        self,
        requirement_id: str,
    ) -> PartialCreditRule:
        """Return the rule for a supported requirement."""

        normalized_id = self._normalize_requirement_id(
            requirement_id
        )

        try:
            return PARTIAL_CREDIT_RULES[normalized_id]
        except KeyError as error:
            raise PartialCreditError(
                "Partial credit is not permitted for requirement "
                f"{normalized_id}."
            ) from error

    def evaluate(
        self,
        requirement_id: str,
        finding: AssessmentFinding | str,
        implementation_state: PartialImplementationState | str,
    ) -> PartialCreditResult:
        """
        Calculate the deduction for a supported partial-credit requirement.

        Args:
            requirement_id:
                CMMC requirement identifier.

            finding:
                Overall assessment finding.

            implementation_state:
                Detailed implementation state used to determine whether
                the adjusted 3-point deduction or full 5-point deduction
                applies.

        Returns:
            PartialCreditResult containing the deduction and explanation.
        """

        normalized_id = self._normalize_requirement_id(
            requirement_id
        )

        rule = self.get_rule(normalized_id)
        normalized_finding = self._coerce_finding(finding)
        normalized_state = self._coerce_state(
            implementation_state
        )

        self._validate_combination(
            requirement_id=normalized_id,
            finding=normalized_finding,
            implementation_state=normalized_state,
        )

        if normalized_finding in {
            AssessmentFinding.MET,
            AssessmentFinding.NOT_APPLICABLE,
        }:
            return PartialCreditResult(
                requirement_id=normalized_id,
                finding=normalized_finding,
                implementation_state=normalized_state,
                deduction_points=0,
                partial_credit_applied=False,
                explanation=(
                    f"{normalized_id} is assessed "
                    f"{normalized_finding.value}; no points are deducted."
                ),
            )

        if normalized_finding == AssessmentFinding.NOT_ASSESSED:
            return PartialCreditResult(
                requirement_id=normalized_id,
                finding=normalized_finding,
                implementation_state=normalized_state,
                deduction_points=0,
                partial_credit_applied=False,
                explanation=(
                    f"{normalized_id} has not been assessed; "
                    "no deduction is calculated yet."
                ),
            )

        if (
            normalized_state
            == PartialImplementationState.PARTIALLY_IMPLEMENTED
        ):
            return PartialCreditResult(
                requirement_id=normalized_id,
                finding=normalized_finding,
                implementation_state=normalized_state,
                deduction_points=rule.partial_deduction_points,
                partial_credit_applied=True,
                explanation=(
                    f"{rule.partial_condition} "
                    f"{rule.partial_deduction_points} points are deducted."
                ),
            )

        return PartialCreditResult(
            requirement_id=normalized_id,
            finding=normalized_finding,
            implementation_state=normalized_state,
            deduction_points=rule.full_deduction_points,
            partial_credit_applied=False,
            explanation=(
                f"{rule.full_deduction_condition} "
                f"{rule.full_deduction_points} points are deducted."
            ),
        )

    def deduction_for(
        self,
        requirement_id: str,
        finding: AssessmentFinding | str,
        implementation_state: PartialImplementationState | str,
    ) -> int:
        """Convenience method returning only the deduction value."""

        return self.evaluate(
            requirement_id=requirement_id,
            finding=finding,
            implementation_state=implementation_state,
        ).deduction_points

    @staticmethod
    def _validate_combination(
        requirement_id: str,
        finding: AssessmentFinding,
        implementation_state: PartialImplementationState,
    ) -> None:
        """
        Reject logically inconsistent finding and implementation-state pairs.
        """

        if finding == AssessmentFinding.MET:
            if (
                implementation_state
                != PartialImplementationState.FULLY_IMPLEMENTED
            ):
                raise PartialCreditError(
                    f"{requirement_id} assessed MET must use "
                    "FULLY IMPLEMENTED as its implementation state."
                )

        elif finding == AssessmentFinding.NOT_APPLICABLE:
            if (
                implementation_state
                != PartialImplementationState.NOT_APPLICABLE
            ):
                raise PartialCreditError(
                    f"{requirement_id} assessed NOT APPLICABLE must use "
                    "NOT APPLICABLE as its implementation state."
                )

        elif finding == AssessmentFinding.NOT_ASSESSED:
            if (
                implementation_state
                != PartialImplementationState.NOT_ASSESSED
            ):
                raise PartialCreditError(
                    f"{requirement_id} assessed NOT ASSESSED must use "
                    "NOT ASSESSED as its implementation state."
                )

        elif finding == AssessmentFinding.NOT_MET:
            if implementation_state not in {
                PartialImplementationState.PARTIALLY_IMPLEMENTED,
                PartialImplementationState.NOT_IMPLEMENTED,
            }:
                raise PartialCreditError(
                    f"{requirement_id} assessed NOT MET must use either "
                    "PARTIALLY IMPLEMENTED or NOT IMPLEMENTED."
                )

    @staticmethod
    def _coerce_finding(
        value: AssessmentFinding | str,
    ) -> AssessmentFinding:
        if isinstance(value, AssessmentFinding):
            return value

        normalized = str(value).strip().upper()

        aliases = {
            "N/A": AssessmentFinding.NOT_APPLICABLE,
            "NA": AssessmentFinding.NOT_APPLICABLE,
            "NOT APPLICABLE": AssessmentFinding.NOT_APPLICABLE,
            "MET": AssessmentFinding.MET,
            "NOT MET": AssessmentFinding.NOT_MET,
            "NOT_MET": AssessmentFinding.NOT_MET,
            "NOT ASSESSED": AssessmentFinding.NOT_ASSESSED,
            "NOT_ASSESSED": AssessmentFinding.NOT_ASSESSED,
        }

        try:
            return aliases[normalized]
        except KeyError as error:
            raise PartialCreditError(
                f"Unsupported assessment finding: {value}"
            ) from error

    @staticmethod
    def _coerce_state(
        value: PartialImplementationState | str,
    ) -> PartialImplementationState:
        if isinstance(value, PartialImplementationState):
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
            raise PartialCreditError(
                f"Unsupported partial implementation state: {value}"
            ) from error

    @staticmethod
    def _normalize_requirement_id(
        requirement_id: str,
    ) -> str:
        normalized = requirement_id.strip().upper()

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