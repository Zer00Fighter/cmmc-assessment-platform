from dataclasses import dataclass


@dataclass(frozen=True)
class Objective:
    requirement_id: str
    objective_id: str
    objective_text: str
    examine: bool
    interview: bool
    test: bool