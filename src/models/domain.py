from dataclasses import dataclass


@dataclass(frozen=True)
class Domain:
    code: str
    name: str
    sequence: int