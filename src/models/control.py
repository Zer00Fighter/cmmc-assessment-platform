from dataclasses import dataclass


@dataclass(frozen=True)
class Control:
    domain_code: str
    requirement_id: str
    title: str
    statement: str
    deduction_points: int
    poam_eligible: bool
    source_reference: str = ""

    def __post_init__(self) -> None:
        if self.deduction_points not in {1, 3, 5}:
            raise ValueError(
                "deduction_points must be one of: 1, 3, or 5"
            )