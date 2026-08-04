from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence

from src.compiler.requirement_parser import RequirementBlock


OBJECTIVE_PATTERN = re.compile(
    r"^\[(?P<objective_id>[a-z])\]\s*"
    r"(?P<objective_text>.+)$",
    re.IGNORECASE,
)

REFERENCE_PATTERN = re.compile(
    r"^[•\-]\s*(?P<reference>.+)$"
)

REQUIREMENT_HEADING_PATTERN = re.compile(
    r"^[A-Z]{2}\.L2-3\.\d+\.\d+"
    r"\s*[-–—]\s*.+$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedObjective:
    requirement_id: str
    objective_id: str
    objective_text: str


@dataclass(frozen=True)
class ParsedRequirement:
    requirement_id: str
    domain_code: str
    title: str
    statement: str
    objectives: List[ParsedObjective]
    examine_objects: List[str]
    interview_objects: List[str]
    test_objects: List[str]
    key_references: List[str]
    source_page_start: int
    source_page_end: int


class ContentParser:
    """
    Convert a raw RequirementBlock into structured CMMC requirement data.

    Expected section order:

    1. Requirement heading
    2. Requirement statement
    3. Assessment objectives
    4. Potential assessment methods and objects
    5. Discussion
    6. Further discussion
    7. Key references
    """

    def parse(
        self,
        block: RequirementBlock,
    ) -> ParsedRequirement:
        lines = self._prepare_lines(block.raw_text)

        statement = self._extract_statement(lines)

        objectives = self._extract_objectives(
            requirement_id=block.requirement_id,
            lines=lines,
        )

        examine_objects = self._extract_method_objects(
            lines=lines,
            method_name="EXAMINE",
        )

        interview_objects = self._extract_method_objects(
            lines=lines,
            method_name="INTERVIEW",
        )

        test_objects = self._extract_method_objects(
            lines=lines,
            method_name="TEST",
        )

        key_references = self._extract_key_references(lines)

        return ParsedRequirement(
            requirement_id=block.requirement_id,
            domain_code=block.domain_code,
            title=self._clean_title(block.title),
            statement=statement,
            objectives=objectives,
            examine_objects=examine_objects,
            interview_objects=interview_objects,
            test_objects=test_objects,
            key_references=key_references,
            source_page_start=block.source_page_start,
            source_page_end=block.source_page_end,
        )

    def parse_many(
        self,
        blocks: Sequence[RequirementBlock],
    ) -> List[ParsedRequirement]:
        return [self.parse(block) for block in blocks]

    def _extract_statement(
        self,
        lines: Sequence[str],
    ) -> str:
        """
        Extract the official requirement statement.

        PDF text may repeat the domain name, page heading, requirement
        heading, and title before the actual statement.
        """

        if not lines:
            return ""

        statement_lines: List[str] = []
        heading_seen = False

        for line in lines:
            upper_line = line.upper().strip()

            if "ASSESSMENT OBJECTIVES" in upper_line:
                break

            if self._is_page_header_or_footer(line):
                continue

            if REQUIREMENT_HEADING_PATTERN.match(line):
                heading_seen = True
                continue

            if not heading_seen:
                continue

            # Skip domain labels such as "Access Control (AC)".
            if re.fullmatch(
                r"[A-Za-z][A-Za-z &/\-]+ \([A-Z]{2}\)",
                line,
            ):
                continue

            # Skip short all-uppercase title repetitions.
            if (
                line.isupper()
                and len(line.split()) <= 14
                and not line.endswith(".")
            ):
                continue

            statement_lines.append(line)

        return self._join_wrapped_lines(statement_lines)

    def _extract_objectives(
        self,
        requirement_id: str,
        lines: Sequence[str],
    ) -> List[ParsedObjective]:
        section_lines = self._extract_section(
            lines=lines,
            start_marker="ASSESSMENT OBJECTIVES",
            end_markers=(
                "POTENTIAL ASSESSMENT METHODS AND OBJECTS",
                "DISCUSSION",
            ),
        )

        objectives: List[ParsedObjective] = []

        current_id: str | None = None
        current_text_parts: List[str] = []

        for line in section_lines:
            upper_line = line.upper()

            if upper_line.startswith("DETERMINE IF"):
                continue

            match = OBJECTIVE_PATTERN.match(line)

            if match:
                if current_id is not None:
                    objectives.append(
                        ParsedObjective(
                            requirement_id=requirement_id,
                            objective_id=current_id,
                            objective_text=self._join_wrapped_lines(
                                current_text_parts
                            ),
                        )
                    )

                current_id = (
                    match.group("objective_id")
                    .strip()
                    .lower()
                )

                current_text_parts = [
                    match.group("objective_text").strip()
                ]

            elif current_id is not None:
                current_text_parts.append(line)

        if current_id is not None:
            objectives.append(
                ParsedObjective(
                    requirement_id=requirement_id,
                    objective_id=current_id,
                    objective_text=self._join_wrapped_lines(
                        current_text_parts
                    ),
                )
            )

        return objectives

    def _extract_method_objects(
        self,
        lines: Sequence[str],
        method_name: str,
    ) -> List[str]:
        methods_section = self._extract_section(
            lines=lines,
            start_marker=(
                "POTENTIAL ASSESSMENT METHODS AND OBJECTS"
            ),
            end_markers=(
                "DISCUSSION",
                "FURTHER DISCUSSION",
                "KEY REFERENCES",
            ),
        )

        target_method = method_name.upper()

        valid_method_names = {
            "EXAMINE",
            "INTERVIEW",
            "TEST",
        }

        if target_method not in valid_method_names:
            raise ValueError(
                f"Unsupported assessment method: {method_name}"
            )

        collecting = False
        collected_lines: List[str] = []

        for line in methods_section:
            upper_line = line.upper().strip()

            if upper_line == target_method:
                collecting = True
                continue

            if collecting and upper_line in valid_method_names:
                break

            if collecting:
                collected_lines.append(line)

        combined_text = self._join_wrapped_lines(
            collected_lines
        )

        return self._parse_select_from_objects(combined_text)

    def _parse_select_from_objects(
        self,
        text: str,
    ) -> List[str]:
        """
        Parse content such as:

        [SELECT FROM: Access control policy; procedures;
        system security plan; other relevant documents or records].
        """

        if not text:
            return []

        cleaned = text.strip()

        cleaned = re.sub(
            r"^\[?\s*SELECT FROM:\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = cleaned.rstrip("]. ")

        objects = [
            self._normalize_whitespace(item)
            for item in cleaned.split(";")
        ]

        return [item for item in objects if item]

    def _extract_key_references(
        self,
        lines: Sequence[str],
    ) -> List[str]:
        reference_lines = self._extract_section(
            lines=lines,
            start_marker="KEY REFERENCES",
            end_markers=(),
        )

        references: List[str] = []
        current_reference: List[str] = []

        for line in reference_lines:
            match = REFERENCE_PATTERN.match(line)

            if match:
                if current_reference:
                    references.append(
                        self._join_wrapped_lines(
                            current_reference
                        )
                    )

                current_reference = [
                    match.group("reference").strip()
                ]

            elif current_reference:
                current_reference.append(line)

        if current_reference:
            references.append(
                self._join_wrapped_lines(
                    current_reference
                )
            )

        return references

    def _extract_section(
        self,
        lines: Sequence[str],
        start_marker: str,
        end_markers: Sequence[str],
    ) -> List[str]:
        collecting = False
        section_lines: List[str] = []

        for line in lines:
            upper_line = line.upper()

            if not collecting:
                if start_marker.upper() in upper_line:
                    collecting = True
                continue

            if any(
                marker.upper() in upper_line
                for marker in end_markers
            ):
                break

            if self._is_page_header_or_footer(line):
                continue

            section_lines.append(line)

        return section_lines

    def _prepare_lines(
        self,
        raw_text: str,
    ) -> List[str]:
        prepared: List[str] = []

        for raw_line in raw_text.splitlines():
            line = self._normalize_whitespace(raw_line)

            if not line:
                continue

            if self._is_page_header_or_footer(line):
                continue

            prepared.append(line)

        return prepared

    @staticmethod
    def _clean_title(title: str) -> str:
        return ContentParser._normalize_whitespace(title)

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        cleaned = (
            text.replace("\u00ad", "")
            .replace("\u2013", "-")
            .replace("\u2014", "-")
            .replace("\ufeff", "")
        )

        return " ".join(cleaned.split())

    @staticmethod
    def _join_wrapped_lines(
        lines: Sequence[str],
    ) -> str:
        if not lines:
            return ""

        result = ""

        for line in lines:
            cleaned = ContentParser._normalize_whitespace(
                line
            )

            if not cleaned:
                continue

            if result.endswith("-"):
                result = result[:-1] + cleaned
            elif not result:
                result = cleaned
            else:
                result += " " + cleaned

        return result.strip()

    @staticmethod
    def _is_page_header_or_footer(
        line: str,
    ) -> bool:
        normalized = ContentParser._normalize_whitespace(
            line
        )
        upper_line = normalized.upper()

        if "CMMC ASSESSMENT GUIDE" in upper_line:
            return True

        if upper_line.startswith("VERSION 2.13"):
            return True

        if upper_line.startswith("DOD-CIO-"):
            return True

        if re.fullmatch(r"\d+", normalized):
            return True

        if re.fullmatch(
            r"[IVXLCDM]+",
            upper_line,
        ):
            return True

        return False