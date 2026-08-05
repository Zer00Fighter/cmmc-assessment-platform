from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Sequence


# ---------------------------------------------------------------------------
# Official 32 CFR § 170.24 Level 2 scoring assignments
# ---------------------------------------------------------------------------

FIVE_POINT_BASIC_REQUIREMENTS = {
    "AC.L2-3.1.1",
    "AC.L2-3.1.2",
    "AT.L2-3.2.1",
    "AT.L2-3.2.2",
    "AU.L2-3.3.1",
    "CM.L2-3.4.1",
    "CM.L2-3.4.2",
    "IA.L2-3.5.1",
    "IA.L2-3.5.2",
    "IR.L2-3.6.1",
    "IR.L2-3.6.2",
    "MA.L2-3.7.2",
    "MP.L2-3.8.3",
    "PS.L2-3.9.2",
    "PE.L2-3.10.1",
    "PE.L2-3.10.2",
    "CA.L2-3.12.1",
    "CA.L2-3.12.3",
    "SC.L2-3.13.1",
    "SC.L2-3.13.2",
    "SI.L2-3.14.1",
    "SI.L2-3.14.2",
    "SI.L2-3.14.3",
}


FIVE_POINT_DERIVED_REQUIREMENTS = {
    "AC.L2-3.1.12",
    "AC.L2-3.1.13",
    "AC.L2-3.1.16",
    "AC.L2-3.1.17",
    "AC.L2-3.1.18",
    "AU.L2-3.3.5",
    "CM.L2-3.4.5",
    "CM.L2-3.4.6",
    "CM.L2-3.4.7",
    "CM.L2-3.4.8",
    "IA.L2-3.5.10",
    "MA.L2-3.7.5",
    "MP.L2-3.8.7",
    "RA.L2-3.11.2",
    "SC.L2-3.13.5",
    "SC.L2-3.13.6",
    "SC.L2-3.13.15",
    "SI.L2-3.14.4",
    "SI.L2-3.14.6",
}


FIVE_POINT_REQUIREMENTS = (
    FIVE_POINT_BASIC_REQUIREMENTS
    | FIVE_POINT_DERIVED_REQUIREMENTS
)


THREE_POINT_BASIC_REQUIREMENTS = {
    "AU.L2-3.3.2",
    "MA.L2-3.7.1",
    "MP.L2-3.8.1",
    "MP.L2-3.8.2",
    "PS.L2-3.9.1",
    "RA.L2-3.11.1",
    "CA.L2-3.12.2",
}


THREE_POINT_DERIVED_REQUIREMENTS = {
    "AC.L2-3.1.5",
    "AC.L2-3.1.19",
    "MA.L2-3.7.4",
    "MP.L2-3.8.8",
    "SC.L2-3.13.8",
    "SI.L2-3.14.5",
    "SI.L2-3.14.7",
}


THREE_POINT_REQUIREMENTS = (
    THREE_POINT_BASIC_REQUIREMENTS
    | THREE_POINT_DERIVED_REQUIREMENTS
)


# These requirements may receive a deduction of either 3 or 5 points.
PARTIAL_CREDIT_REQUIREMENTS: Dict[str, Dict[str, object]] = {
    "IA.L2-3.5.3": {
        "partial_deduction_points": 3,
        "full_deduction_points": 5,
        "partial_credit_condition": (
            "MFA is implemented only for remote and privileged users."
        ),
        "full_deduction_condition": (
            "MFA is not implemented for any users."
        ),
    },
    "SC.L2-3.13.11": {
        "partial_deduction_points": 3,
        "full_deduction_points": 5,
        "partial_credit_condition": (
            "Encryption is employed, but it is not FIPS-validated."
        ),
        "full_deduction_condition": (
            "Encryption is not employed."
        ),
    },
}


# ---------------------------------------------------------------------------
# Expected scoring characteristics
# ---------------------------------------------------------------------------

EXPECTED_REQUIREMENT_COUNT = 110
EXPECTED_FIVE_POINT_COUNT = 42
EXPECTED_THREE_POINT_COUNT = 14
EXPECTED_PARTIAL_CREDIT_COUNT = 2
EXPECTED_ONE_POINT_COUNT = 52

MAXIMUM_SCORE = 110
EXPECTED_MAXIMUM_DEDUCTION = 314
EXPECTED_MINIMUM_SCORE = -204

SCORING_SOURCE = "32 CFR 170.24(c)(2)"
SCORING_SOURCE_VERSION = "Current eCFR"


@dataclass(frozen=True)
class ScoringWeight:
    """Scoring metadata for one CMMC Level 2 requirement."""

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


class ScoringCompiler:
    """
    Compile the CMMC Level 2 scoring table.

    Input:
        data/controls/cmmc_level2_controls.csv

    Output:
        data/scoring/scoring_weights.csv

    Requirement scoring is assigned according to 32 CFR § 170.24(c)(2).
    """

    def __init__(
        self,
        controls_csv: Path,
        output_csv: Path,
    ) -> None:
        self.controls_csv = controls_csv.resolve()
        self.output_csv = output_csv.resolve()

    def compile(self) -> List[ScoringWeight]:
        """Compile, validate, export, and return all scoring rows."""

        requirement_ids = self._load_requirement_ids()

        weights = [
            self._build_weight(requirement_id)
            for requirement_id in requirement_ids
        ]

        self._validate(weights)
        self._write_csv(weights)

        return weights

    def _load_requirement_ids(self) -> List[str]:
        """Load the 110 requirement IDs from the compiled controls file."""

        if not self.controls_csv.exists():
            raise FileNotFoundError(
                f"Controls CSV not found: {self.controls_csv}. "
                "Run python compile_guide.py first."
            )

        with self.controls_csv.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            if reader.fieldnames is None:
                raise ValueError(
                    f"Controls CSV has no header: {self.controls_csv}"
                )

            if "requirement_id" not in reader.fieldnames:
                raise ValueError(
                    "Controls CSV is missing the requirement_id column."
                )

            rows = list(reader)

        requirement_ids = [
            self._normalize_requirement_id(
                row["requirement_id"]
            )
            for row in rows
            if row.get("requirement_id", "").strip()
        ]

        if len(requirement_ids) != EXPECTED_REQUIREMENT_COUNT:
            raise ValueError(
                f"Expected {EXPECTED_REQUIREMENT_COUNT} compiled "
                f"requirements, but found {len(requirement_ids)}."
            )

        duplicate_ids = self._find_duplicates(requirement_ids)

        if duplicate_ids:
            raise ValueError(
                "Duplicate requirement IDs found in controls CSV: "
                + ", ".join(duplicate_ids)
            )

        return requirement_ids

    def _build_weight(
        self,
        requirement_id: str,
    ) -> ScoringWeight:
        """Build the scoring metadata for one requirement."""

        partial_rule = PARTIAL_CREDIT_REQUIREMENTS.get(
            requirement_id
        )

        if partial_rule is not None:
            return ScoringWeight(
                requirement_id=requirement_id,
                domain_code=requirement_id[:2],
                scoring_category="PARTIAL_3_OR_5",
                deduction_points=5,
                partial_credit_allowed=True,
                partial_deduction_points=int(
                    partial_rule[
                        "partial_deduction_points"
                    ]
                ),
                full_deduction_points=int(
                    partial_rule[
                        "full_deduction_points"
                    ]
                ),
                partial_credit_condition=str(
                    partial_rule[
                        "partial_credit_condition"
                    ]
                ),
                full_deduction_condition=str(
                    partial_rule[
                        "full_deduction_condition"
                    ]
                ),
                scoring_source=SCORING_SOURCE,
                scoring_source_version=(
                    SCORING_SOURCE_VERSION
                ),
            )

        if requirement_id in FIVE_POINT_REQUIREMENTS:
            return ScoringWeight(
                requirement_id=requirement_id,
                domain_code=requirement_id[:2],
                scoring_category="FIVE_POINT",
                deduction_points=5,
                partial_credit_allowed=False,
                partial_deduction_points=0,
                full_deduction_points=5,
                partial_credit_condition="",
                full_deduction_condition=(
                    "Requirement is assessed NOT MET."
                ),
                scoring_source=SCORING_SOURCE,
                scoring_source_version=(
                    SCORING_SOURCE_VERSION
                ),
            )

        if requirement_id in THREE_POINT_REQUIREMENTS:
            return ScoringWeight(
                requirement_id=requirement_id,
                domain_code=requirement_id[:2],
                scoring_category="THREE_POINT",
                deduction_points=3,
                partial_credit_allowed=False,
                partial_deduction_points=0,
                full_deduction_points=3,
                partial_credit_condition="",
                full_deduction_condition=(
                    "Requirement is assessed NOT MET."
                ),
                scoring_source=SCORING_SOURCE,
                scoring_source_version=(
                    SCORING_SOURCE_VERSION
                ),
            )

        return ScoringWeight(
            requirement_id=requirement_id,
            domain_code=requirement_id[:2],
            scoring_category="ONE_POINT",
            deduction_points=1,
            partial_credit_allowed=False,
            partial_deduction_points=0,
            full_deduction_points=1,
            partial_credit_condition="",
            full_deduction_condition=(
                "Requirement is assessed NOT MET."
            ),
            scoring_source=SCORING_SOURCE,
            scoring_source_version=(
                SCORING_SOURCE_VERSION
            ),
        )

    def _validate(
        self,
        weights: Sequence[ScoringWeight],
    ) -> None:
        """Validate all scoring assignments before writing the CSV."""

        if len(weights) != EXPECTED_REQUIREMENT_COUNT:
            raise ValueError(
                f"Expected {EXPECTED_REQUIREMENT_COUNT} scoring rows, "
                f"but found {len(weights)}."
            )

        requirement_ids = [
            weight.requirement_id
            for weight in weights
        ]

        duplicate_ids = self._find_duplicates(
            requirement_ids
        )

        if duplicate_ids:
            raise ValueError(
                "Duplicate requirement IDs found in scoring table: "
                + ", ".join(duplicate_ids)
            )

        requirement_id_set = set(requirement_ids)

        self._validate_no_overlapping_categories()

        self._validate_required_ids_present(
            requirement_id_set
        )

        five_point_rows = [
            weight
            for weight in weights
            if weight.scoring_category == "FIVE_POINT"
        ]

        three_point_rows = [
            weight
            for weight in weights
            if weight.scoring_category == "THREE_POINT"
        ]

        partial_rows = [
            weight
            for weight in weights
            if weight.scoring_category == "PARTIAL_3_OR_5"
        ]

        one_point_rows = [
            weight
            for weight in weights
            if weight.scoring_category == "ONE_POINT"
        ]

        if len(five_point_rows) != EXPECTED_FIVE_POINT_COUNT:
            raise ValueError(
                f"Expected {EXPECTED_FIVE_POINT_COUNT} five-point "
                f"requirements, but found {len(five_point_rows)}."
            )

        if len(three_point_rows) != EXPECTED_THREE_POINT_COUNT:
            raise ValueError(
                f"Expected {EXPECTED_THREE_POINT_COUNT} three-point "
                f"requirements, but found {len(three_point_rows)}."
            )

        if len(partial_rows) != EXPECTED_PARTIAL_CREDIT_COUNT:
            raise ValueError(
                f"Expected {EXPECTED_PARTIAL_CREDIT_COUNT} partial-credit "
                f"requirements, but found {len(partial_rows)}."
            )

        if len(one_point_rows) != EXPECTED_ONE_POINT_COUNT:
            raise ValueError(
                f"Expected {EXPECTED_ONE_POINT_COUNT} one-point "
                f"requirements, but found {len(one_point_rows)}."
            )

        invalid_deductions = [
            weight.requirement_id
            for weight in weights
            if weight.deduction_points not in {1, 3, 5}
        ]

        if invalid_deductions:
            raise ValueError(
                "Invalid deduction points for: "
                + ", ".join(invalid_deductions)
            )

        invalid_partial_rows = [
            weight.requirement_id
            for weight in partial_rows
            if (
                weight.partial_deduction_points != 3
                or weight.full_deduction_points != 5
            )
        ]

        if invalid_partial_rows:
            raise ValueError(
                "Invalid partial-credit configuration for: "
                + ", ".join(invalid_partial_rows)
            )

        total_possible_deduction = sum(
            weight.full_deduction_points
            for weight in weights
        )

        if (
            total_possible_deduction
            != EXPECTED_MAXIMUM_DEDUCTION
        ):
            raise ValueError(
                "Expected total possible deduction of "
                f"{EXPECTED_MAXIMUM_DEDUCTION}, but calculated "
                f"{total_possible_deduction}."
            )

        minimum_score = (
            MAXIMUM_SCORE
            - total_possible_deduction
        )

        if minimum_score != EXPECTED_MINIMUM_SCORE:
            raise ValueError(
                f"Expected mathematical minimum score of "
                f"{EXPECTED_MINIMUM_SCORE}, but calculated "
                f"{minimum_score}."
            )

    @staticmethod
    def _validate_no_overlapping_categories() -> None:
        """Ensure no requirement is assigned to multiple fixed categories."""

        five_and_three = (
            FIVE_POINT_REQUIREMENTS
            & THREE_POINT_REQUIREMENTS
        )

        five_and_partial = (
            FIVE_POINT_REQUIREMENTS
            & set(PARTIAL_CREDIT_REQUIREMENTS)
        )

        three_and_partial = (
            THREE_POINT_REQUIREMENTS
            & set(PARTIAL_CREDIT_REQUIREMENTS)
        )

        overlaps = (
            five_and_three
            | five_and_partial
            | three_and_partial
        )

        if overlaps:
            raise ValueError(
                "Requirements appear in multiple scoring categories: "
                + ", ".join(sorted(overlaps))
            )

    @staticmethod
    def _validate_required_ids_present(
        requirement_ids: set[str],
    ) -> None:
        """Confirm that every explicitly scored requirement is present."""

        explicitly_scored_ids = (
            FIVE_POINT_REQUIREMENTS
            | THREE_POINT_REQUIREMENTS
            | set(PARTIAL_CREDIT_REQUIREMENTS)
        )

        missing_ids = (
            explicitly_scored_ids
            - requirement_ids
        )

        if missing_ids:
            raise ValueError(
                "Official scoring requirements are missing from "
                "the compiled controls: "
                + ", ".join(sorted(missing_ids))
            )

    def _write_csv(
        self,
        weights: Sequence[ScoringWeight],
    ) -> None:
        """Write the validated scoring table."""

        self.output_csv.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fieldnames = [
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
        ]

        with self.output_csv.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
                extrasaction="raise",
            )

            writer.writeheader()

            for weight in weights:
                row = asdict(weight)

                row["partial_credit_allowed"] = (
                    "Yes"
                    if weight.partial_credit_allowed
                    else "No"
                )

                writer.writerow(row)

    @staticmethod
    def _normalize_requirement_id(
        requirement_id: str,
    ) -> str:
        """
        Normalize typographical variations found in source documents.

        For example:
            IA-L2-3.5.1 -> IA.L2-3.5.1
        """

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

    @staticmethod
    def _find_duplicates(
        values: Sequence[str],
    ) -> List[str]:
        seen: set[str] = set()
        duplicates: set[str] = set()

        for value in values:
            if value in seen:
                duplicates.add(value)
            else:
                seen.add(value)

        return sorted(duplicates)