from dataclasses import dataclass
from datetime import date
from typing import Optional


VALID_STATUSES = {
    "MET",
    "NOT MET",
    "NOT APPLICABLE",
    "NOT ASSESSED",
}


@dataclass
class AssessmentRecord:
    requirement_id: str
    status: str = "NOT ASSESSED"
    assessor: str = ""
    assessment_date: Optional[date] = None
    notes: str = ""
    evidence_complete: bool = False
    ssp_reference: str = ""

    def __post_init__(self) -> None:
        normalized_status = self.status.strip().upper()

        if normalized_status not in VALID_STATUSES:
            raise ValueError(
                f"Unsupported assessment status: {self.status}. "
                f"Expected one of: {sorted(VALID_STATUSES)}"
            )

        self.status = normalized_status