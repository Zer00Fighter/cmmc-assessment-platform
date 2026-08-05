from dataclasses import dataclass


@dataclass(frozen=True)
class Objective:
    requirement_id: str
    objective_id: str
    objective_text: str
    source_page_start: int
    source_page_end: int
    source_document: str = ""
    source_version: str = ""