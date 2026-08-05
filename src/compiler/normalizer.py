from __future__ import annotations

import re
import unicodedata
from typing import Iterable, List, Sequence

from src.compiler.content_parser import (
    ParsedObjective,
    ParsedRequirement,
)


class TextNormalizer:
    """
    Normalize text extracted from the CMMC Assessment Guide PDF.

    The normalizer removes common PDF extraction artifacts while preserving
    requirement IDs, objective IDs, official wording, and source meaning.
    """

    _PAGE_NUMBER_PATTERN = re.compile(r"^\d+$")

    _ROMAN_PAGE_PATTERN = re.compile(
        r"^[IVXLCDM]+$",
        re.IGNORECASE,
    )

    _REQUIREMENT_ID_PATTERN = re.compile(
        r"\b[A-Z]{2}\.L2-3\.\d+\.\d+\b"
    )

    _OBJECTIVE_ID_PATTERN = re.compile(
        r"^\[[a-z]\]",
        re.IGNORECASE,
    )

    _MULTISPACE_PATTERN = re.compile(r"[ \t]+")
    _MULTIBLANK_PATTERN = re.compile(r"\n{3,}")

    _HEADER_PATTERNS = (
        re.compile(
            r"^CMMC Assessment Guide.*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^Version 2\.13.*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^DoD-CIO-.*$",
            re.IGNORECASE,
        ),
    )

    def normalize_requirement(
        self,
        requirement: ParsedRequirement,
    ) -> ParsedRequirement:
        """
        Return a normalized copy of a parsed requirement.
        """

        normalized_objectives = [
            ParsedObjective(
                requirement_id=objective.requirement_id,
                objective_id=objective.objective_id.lower(),
                objective_text=self.normalize_objective(
                    objective.objective_text
                ),
            )
            for objective in requirement.objectives
        ]

        return ParsedRequirement(
            requirement_id=requirement.requirement_id,
            domain_code=requirement.domain_code,
            title=self.normalize_title(requirement.title),
            statement=self.normalize_statement(
                requirement.statement
            ),
            objectives=normalized_objectives,
            examine_objects=self.normalize_items(
                requirement.examine_objects
            ),
            interview_objects=self.normalize_items(
                requirement.interview_objects
            ),
            test_objects=self.normalize_items(
                requirement.test_objects
            ),
            key_references=self.normalize_references(
                requirement.key_references
            ),
            source_page_start=requirement.source_page_start,
            source_page_end=requirement.source_page_end,
        )

    def normalize_many(
        self,
        requirements: Sequence[ParsedRequirement],
    ) -> List[ParsedRequirement]:
        return [
            self.normalize_requirement(requirement)
            for requirement in requirements
        ]

    def normalize_text(
        self,
        text: str,
    ) -> str:
        """
        Apply general-purpose text normalization.
        """

        if not text:
            return ""

        normalized = self.normalize_unicode(text)
        normalized = self.remove_soft_hyphens(normalized)
        normalized = self.normalize_line_endings(normalized)
        normalized = self.remove_headers_and_footers(
            normalized
        )
        normalized = self.join_wrapped_lines(normalized)
        normalized = self.collapse_whitespace(normalized)

        return normalized.strip()

    def normalize_title(
        self,
        title: str,
    ) -> str:
        normalized = self.normalize_text(title)

        return normalized.strip(" -–—")

    def normalize_statement(
        self,
        statement: str,
    ) -> str:
        normalized = self.normalize_text(statement)

        return self._ensure_terminal_punctuation(normalized)

    def normalize_objective(
        self,
        objective_text: str,
    ) -> str:
        normalized = self.normalize_text(objective_text)

        normalized = re.sub(
            r"^[;\s]+",
            "",
            normalized,
        )

        return normalized

    def normalize_reference(
        self,
        reference: str,
    ) -> str:
        normalized = self.normalize_text(reference)

        normalized = normalized.lstrip("•- ")

        return normalized.strip()

    def normalize_references(
        self,
        references: Iterable[str],
    ) -> List[str]:
        normalized: List[str] = []
        seen: set[str] = set()

        for reference in references:
            cleaned = self.normalize_reference(reference)

            if not cleaned:
                continue

            key = cleaned.casefold()

            if key in seen:
                continue

            seen.add(key)
            normalized.append(cleaned)

        return normalized

    def normalize_item(
        self,
        item: str,
    ) -> str:
        normalized = self.normalize_text(item)

        normalized = normalized.strip("[];,. ")

        return normalized

    def normalize_items(
        self,
        items: Iterable[str],
    ) -> List[str]:
        normalized: List[str] = []
        seen: set[str] = set()

        for item in items:
            cleaned = self.normalize_item(item)

            if not cleaned:
                continue

            key = cleaned.casefold()

            if key in seen:
                continue

            seen.add(key)
            normalized.append(cleaned)

        return normalized

    def normalize_unicode(
        self,
        text: str,
    ) -> str:
        """
        Normalize Unicode without altering requirement or objective IDs.
        """

        normalized = unicodedata.normalize(
            "NFKC",
            text,
        )

        replacements = {
            "\u2010": "-",
            "\u2011": "-",
            "\u2012": "-",
            "\u2013": "-",
            "\u2014": "-",
            "\u2212": "-",
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2022": "•",
            "\ufeff": "",
            "\u00a0": " ",
        }

        for source, replacement in replacements.items():
            normalized = normalized.replace(
                source,
                replacement,
            )

        return normalized

    @staticmethod
    def remove_soft_hyphens(
        text: str,
    ) -> str:
        return text.replace("\u00ad", "")

    @staticmethod
    def normalize_line_endings(
        text: str,
    ) -> str:
        return (
            text.replace("\r\n", "\n")
            .replace("\r", "\n")
        )

    def remove_headers_and_footers(
        self,
        text: str,
    ) -> str:
        cleaned_lines: List[str] = []

        for raw_line in text.splitlines():
            line = self._collapse_inline_whitespace(
                raw_line
            ).strip()

            if not line:
                cleaned_lines.append("")
                continue

            if self._is_header_or_footer(line):
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def join_wrapped_lines(
        self,
        text: str,
    ) -> str:
        """
        Join PDF-wrapped lines while preserving paragraph breaks.

        Lines ending with a hyphen are joined without an inserted space.
        Blank lines preserve paragraph boundaries.
        """

        paragraphs: List[str] = []
        current_parts: List[str] = []

        for raw_line in text.splitlines():
            line = self._collapse_inline_whitespace(
                raw_line
            ).strip()

            if not line:
                if current_parts:
                    paragraphs.append(
                        self._join_line_parts(
                            current_parts
                        )
                    )
                    current_parts = []

                continue

            current_parts.append(line)

        if current_parts:
            paragraphs.append(
                self._join_line_parts(current_parts)
            )

        return "\n\n".join(paragraphs)

    def collapse_whitespace(
        self,
        text: str,
    ) -> str:
        lines = [
            self._collapse_inline_whitespace(line).strip()
            for line in text.splitlines()
        ]

        normalized = "\n".join(lines)
        normalized = self._MULTIBLANK_PATTERN.sub(
            "\n\n",
            normalized,
        )

        return normalized.strip()

    def _is_header_or_footer(
        self,
        line: str,
    ) -> bool:
        if self._PAGE_NUMBER_PATTERN.fullmatch(line):
            return True

        if self._ROMAN_PAGE_PATTERN.fullmatch(line):
            return True

        for pattern in self._HEADER_PATTERNS:
            if pattern.match(line):
                return True

        return False

    @staticmethod
    def _collapse_inline_whitespace(
        text: str,
    ) -> str:
        return TextNormalizer._MULTISPACE_PATTERN.sub(
            " ",
            text,
        )

    @staticmethod
    def _join_line_parts(
        parts: Sequence[str],
    ) -> str:
        result = ""

        for part in parts:
            if not result:
                result = part
                continue

            if result.endswith("-"):
                result = result[:-1] + part
            else:
                result += " " + part

        return result.strip()

    @staticmethod
    def _ensure_terminal_punctuation(
        text: str,
    ) -> str:
        if not text:
            return ""

        if text.endswith((".", ";", ":", "?", "!")):
            return text

        return f"{text}."