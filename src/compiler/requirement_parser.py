from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence

from src.compiler.pdf_extractor import ExtractedPage


REQUIREMENT_HEADING_PATTERN = re.compile(
    r"^(?P<requirement_id>[A-Z]{2}\.L2-3\.\d+\.\d+)"
    r"\s*[–—-]\s*"
    r"(?P<title>.+?)\s*$"
)


@dataclass(frozen=True)
class RequirementBlock:
    requirement_id: str
    domain_code: str
    title: str
    source_page_start: int
    source_page_end: int
    raw_text: str


@dataclass(frozen=True)
class RequirementHeading:
    requirement_id: str
    domain_code: str
    title: str
    page_number: int
    line_index: int


class RequirementParser:
    def __init__(self, minimum_source_page: int = 20) -> None:
        self.minimum_source_page = minimum_source_page

    def find_headings(
        self,
        pages: Sequence[ExtractedPage],
    ) -> List[RequirementHeading]:
        headings: List[RequirementHeading] = []
        seen_ids: set[str] = set()

        for page in pages:
            if page.page_number < self.minimum_source_page:
                continue

            lines = page.text.splitlines()

            for line_index, line in enumerate(lines):
                normalized_line = self._normalize_line(line)
                match = REQUIREMENT_HEADING_PATTERN.match(
                    normalized_line
                )

                if match is None:
                    continue

                requirement_id = match.group(
                    "requirement_id"
                ).strip()
                title = match.group("title").strip()

                if requirement_id in seen_ids:
                    continue

                if not self._looks_like_requirement_section(
                    lines=lines,
                    heading_line_index=line_index,
                ):
                    continue

                headings.append(
                    RequirementHeading(
                        requirement_id=requirement_id,
                        domain_code=requirement_id[:2],
                        title=title,
                        page_number=page.page_number,
                        line_index=line_index,
                    )
                )

                seen_ids.add(requirement_id)

        return headings

    def parse(
        self,
        pages: Sequence[ExtractedPage],
    ) -> List[RequirementBlock]:
        headings = self.find_headings(pages)

        if not headings:
            return []

        blocks: List[RequirementBlock] = []

        for heading_index, heading in enumerate(headings):
            if heading_index + 1 < len(headings):
                next_heading = headings[heading_index + 1]
            else:
                next_heading = None

            raw_text = self._collect_block_text(
                pages=pages,
                heading=heading,
                next_heading=next_heading,
            )

            source_page_end = (
                next_heading.page_number
                if next_heading is not None
                else pages[-1].page_number
            )

            if (
                next_heading is not None
                and next_heading.page_number
                > heading.page_number
            ):
                source_page_end -= 1

            blocks.append(
                RequirementBlock(
                    requirement_id=heading.requirement_id,
                    domain_code=heading.domain_code,
                    title=heading.title,
                    source_page_start=heading.page_number,
                    source_page_end=source_page_end,
                    raw_text=raw_text.strip(),
                )
            )

        return blocks

    def _collect_block_text(
        self,
        pages: Sequence[ExtractedPage],
        heading: RequirementHeading,
        next_heading: RequirementHeading | None,
    ) -> str:
        collected_lines: List[str] = []

        for page in pages:
            if page.page_number < heading.page_number:
                continue

            if (
                next_heading is not None
                and page.page_number > next_heading.page_number
            ):
                break

            lines = page.text.splitlines()

            start_line = 0
            end_line = len(lines)

            if page.page_number == heading.page_number:
                start_line = heading.line_index

            if (
                next_heading is not None
                and page.page_number == next_heading.page_number
            ):
                end_line = next_heading.line_index

            if end_line > start_line:
                collected_lines.extend(
                    lines[start_line:end_line]
                )

        return "\n".join(collected_lines)

    @staticmethod
    def _normalize_line(line: str) -> str:
        return " ".join(line.replace("\u00ad", "").split())

    @staticmethod
    def _looks_like_requirement_section(
        lines: Sequence[str],
        heading_line_index: int,
    ) -> bool:
        lookahead_end = min(
            heading_line_index + 20,
            len(lines),
        )

        nearby_text = "\n".join(
            lines[heading_line_index:lookahead_end]
        ).upper()

        return (
            "ASSESSMENT OBJECTIVES" in nearby_text
            or "DETERMINE IF" in nearby_text
        )