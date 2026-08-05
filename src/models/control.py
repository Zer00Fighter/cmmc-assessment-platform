from dataclasses import dataclass


@dataclass(frozen=True)
class Control:
    domain_code: str
    requirement_id: str
    title: str
    statement: str
    source_page_start: int
    source_page_end: int
    source_document: str = ""
    source_version: str = ""