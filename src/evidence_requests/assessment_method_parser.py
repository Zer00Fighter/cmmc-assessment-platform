from __future__ import annotations

import hashlib
import re

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List


class AssessmentMethodParserError(ValueError):
    """Raised when assessment method text cannot be parsed."""


class AssessmentMethodType(str, Enum):
    """Framework-neutral assessment method types."""

    EXAMINE = "Examine"
    INTERVIEW = "Interview"
    TEST = "Test"
    OBSERVE = "Observe"
    OTHER = "Other"


class AssessmentObjectType(str, Enum):
    """Canonical assessment-object categories."""

    POLICY = "Policy"
    PROCEDURE = "Procedure"
    PLAN = "Plan"
    SYSTEM_SECURITY_PLAN = "System Security Plan"
    CONFIGURATION = "Configuration"
    CONFIGURATION_BASELINE = "Configuration Baseline"
    SCREENSHOT = "Screenshot"
    LOG = "Log"
    REPORT = "Report"
    RECORD = "Record"
    INVENTORY = "Inventory"
    DIAGRAM = "Diagram"
    CONTRACT = "Contract"
    AGREEMENT = "Agreement"
    INTERCONNECTION = "Interconnection"
    PERSONNEL_RECORD = "Personnel Record"
    TRAINING_RECORD = "Training Record"
    RISK_ASSESSMENT = "Risk Assessment"
    SECURITY_ASSESSMENT = "Security Assessment"
    POAM = "POA&M"
    INTERVIEW_SUBJECT = "Interview Subject"
    TEST_TARGET = "Test Target"
    TECHNICAL_EVIDENCE = "Technical Evidence"
    OTHER = "Other"


@dataclass(frozen=True, slots=True)
class AssessmentObject:
    """
    One normalized object referenced by an assessment method.

    Example:
        raw_text:
            "access control policy"

        title:
            "Access Control Policy"

        canonical_id:
            "EVIDENCE_POLICY_ACCESS_CONTROL"
    """

    canonical_id: str
    object_type: AssessmentObjectType
    title: str
    raw_text: str

    def __post_init__(self) -> None:
        canonical_id = self.canonical_id.strip()
        title = self.title.strip()
        raw_text = self.raw_text.strip()

        if not canonical_id:
            raise AssessmentMethodParserError(
                "AssessmentObject.canonical_id cannot be blank."
            )

        if not title:
            raise AssessmentMethodParserError(
                "AssessmentObject.title cannot be blank."
            )

        if not raw_text:
            raise AssessmentMethodParserError(
                "AssessmentObject.raw_text cannot be blank."
            )

        object.__setattr__(
            self,
            "canonical_id",
            canonical_id,
        )

        object.__setattr__(
            self,
            "title",
            title,
        )

        object.__setattr__(
            self,
            "raw_text",
            raw_text,
        )


@dataclass(frozen=True, slots=True)
class AssessmentMethod:
    """Parsed assessment method and its referenced objects."""

    method_type: AssessmentMethodType
    objects: tuple[AssessmentObject, ...]
    raw_text: str = ""

    @property
    def object_count(self) -> int:
        return len(self.objects)

    @property
    def canonical_ids(self) -> tuple[str, ...]:
        return tuple(
            item.canonical_id
            for item in self.objects
        )


class AssessmentMethodParser:
    """
    Parse framework assessment-method text into normalized objects.

    This parser is deliberately framework-independent.

    It can parse method text from sources such as:
      - NIST SP 800-171A
      - NIST SP 800-53A
      - contractual assessment procedures
      - future framework content packs
    """

    _SELECTION_MARKERS = (
        "[SELECT FROM:",
        "SELECT FROM:",
        "[SELECT:",
        "SELECT:",
    )

    _CANONICAL_ALIASES = {
        "ssp": (
            AssessmentObjectType.SYSTEM_SECURITY_PLAN,
            "System Security Plan",
            "EVIDENCE_SYSTEM_SECURITY_PLAN",
        ),
        "system security plan": (
            AssessmentObjectType.SYSTEM_SECURITY_PLAN,
            "System Security Plan",
            "EVIDENCE_SYSTEM_SECURITY_PLAN",
        ),
        "poam": (
            AssessmentObjectType.POAM,
            "Plan of Action and Milestones",
            "EVIDENCE_POAM",
        ),
        "poa&m": (
            AssessmentObjectType.POAM,
            "Plan of Action and Milestones",
            "EVIDENCE_POAM",
        ),
        "plan of action and milestones": (
            AssessmentObjectType.POAM,
            "Plan of Action and Milestones",
            "EVIDENCE_POAM",
        ),
        "risk assessment": (
            AssessmentObjectType.RISK_ASSESSMENT,
            "Risk Assessment",
            "EVIDENCE_RISK_ASSESSMENT",
        ),
        "security assessment": (
            AssessmentObjectType.SECURITY_ASSESSMENT,
            "Security Assessment",
            "EVIDENCE_SECURITY_ASSESSMENT",
        ),
    }

    def parse(
        self,
        method_type: AssessmentMethodType | str,
        text: object,
    ) -> AssessmentMethod:
        parsed_method_type = (
            self._coerce_method_type(
                method_type
            )
        )

        raw_text = (
            ""
            if text is None
            else str(text).strip()
        )

        if not raw_text:
            return AssessmentMethod(
                method_type=parsed_method_type,
                objects=(),
                raw_text="",
            )

        tokens = self.tokenize(
            raw_text
        )

        objects = tuple(
            self._parse_object(
                token,
                parsed_method_type,
            )
            for token in tokens
            if token.strip()
        )

        return AssessmentMethod(
            method_type=parsed_method_type,
            objects=self._deduplicate_objects(
                objects
            ),
            raw_text=raw_text,
        )

    def tokenize(
        self,
        text: object,
    ) -> List[str]:
        """
        Split raw assessment-method text into individual objects.

        Handles:
          - semicolon-separated items
          - bullet-separated items
          - line-separated items
          - NIST-style [SELECT FROM: ...] wrappers
        """

        if text is None:
            return []

        value = str(text).strip()

        if not value:
            return []

        value = self._strip_selection_wrapper(
            value
        )

        value = value.replace(
            "\r\n",
            "\n",
        ).replace(
            "\r",
            "\n",
        )

        # Normalize common bullets into separators.
        value = re.sub(
            r"[•●▪◦]",
            ";",
            value,
        )

        # Treat semicolons and new lines as object delimiters.
        parts = re.split(
            r";|\n+",
            value,
        )

        result: List[str] = []

        for part in parts:
            cleaned = self._clean_token(
                part
            )

            if cleaned:
                result.append(cleaned)

        return result

    def normalize_title(
        self,
        text: str,
    ) -> str:
        """
        Convert assessment-object wording into a stable human title.

        Examples:
            "access control policy"
                -> "Access Control Policy"

            "procedures addressing account management"
                -> "Account Management Procedures"

            "system security plan"
                -> "System Security Plan"
        """

        normalized = self._normalize_phrase(
            text
        )

        alias = self._CANONICAL_ALIASES.get(
            normalized
        )

        if alias is not None:
            return alias[1]

        if normalized.startswith(
            "procedures addressing "
        ):
            subject = normalized.removeprefix(
                "procedures addressing "
            )

            return (
                f"{self._title_case(subject)} "
                "Procedures"
            )

        if normalized.startswith(
            "procedure addressing "
        ):
            subject = normalized.removeprefix(
                "procedure addressing "
            )

            return (
                f"{self._title_case(subject)} "
                "Procedure"
            )

        return self._title_case(
            normalized
        )

    def classify(
        self,
        text: str,
        method_type: AssessmentMethodType | None = None,
    ) -> AssessmentObjectType:
        normalized = self._normalize_phrase(
            text
        )

        alias = self._CANONICAL_ALIASES.get(
            normalized
        )

        if alias is not None:
            return alias[0]

        if "system security plan" in normalized:
            return (
                AssessmentObjectType
                .SYSTEM_SECURITY_PLAN
            )

        if (
            "plan of action" in normalized
            or "poa&m" in normalized
            or "poam" in normalized
        ):
            return AssessmentObjectType.POAM

        if "policy" in normalized:
            return AssessmentObjectType.POLICY

        if (
            "procedure" in normalized
            or "procedures" in normalized
        ):
            return AssessmentObjectType.PROCEDURE

        if "configuration baseline" in normalized:
            return (
                AssessmentObjectType
                .CONFIGURATION_BASELINE
            )

        if (
            "configuration setting" in normalized
            or "configuration settings" in normalized
            or "configuration" in normalized
        ):
            return AssessmentObjectType.CONFIGURATION

        if "screenshot" in normalized:
            return AssessmentObjectType.SCREENSHOT

        if (
            "audit log" in normalized
            or normalized.endswith(" logs")
            or normalized.endswith(" log")
            or "event log" in normalized
        ):
            return AssessmentObjectType.LOG

        if "inventory" in normalized:
            return AssessmentObjectType.INVENTORY

        if "diagram" in normalized:
            return AssessmentObjectType.DIAGRAM

        if "contract" in normalized:
            return AssessmentObjectType.CONTRACT

        if "agreement" in normalized:
            return AssessmentObjectType.AGREEMENT

        if "interconnection" in normalized:
            return AssessmentObjectType.INTERCONNECTION

        if "training record" in normalized:
            return AssessmentObjectType.TRAINING_RECORD

        if (
            "personnel record" in normalized
            or "background check" in normalized
        ):
            return AssessmentObjectType.PERSONNEL_RECORD

        if "risk assessment" in normalized:
            return AssessmentObjectType.RISK_ASSESSMENT

        if "security assessment" in normalized:
            return AssessmentObjectType.SECURITY_ASSESSMENT

        if "report" in normalized:
            return AssessmentObjectType.REPORT

        if (
            normalized.endswith(" record")
            or normalized.endswith(" records")
        ):
            return AssessmentObjectType.RECORD

        if normalized.endswith(" plan"):
            return AssessmentObjectType.PLAN

        if (
            method_type
            == AssessmentMethodType.INTERVIEW
        ):
            return (
                AssessmentObjectType
                .INTERVIEW_SUBJECT
            )

        if (
            method_type
            == AssessmentMethodType.TEST
        ):
            return (
                AssessmentObjectType
                .TEST_TARGET
            )

        return AssessmentObjectType.OTHER

    def canonical_id(
        self,
        text: str,
        object_type: AssessmentObjectType | None = None,
    ) -> str:
        normalized = self._normalize_phrase(
            text
        )

        alias = self._CANONICAL_ALIASES.get(
            normalized
        )

        if alias is not None:
            return alias[2]

        object_type = (
            object_type
            or self.classify(text)
        )

        title = self.normalize_title(
            text
        )

        semantic = self._semantic_tokens(
            title
        )

        type_prefix = self._type_prefix(
            object_type
        )

        if semantic:
            candidate = (
                f"EVIDENCE_{type_prefix}_"
                + "_".join(semantic)
            )
        else:
            digest = hashlib.sha1(
                normalized.encode(
                    "utf-8"
                )
            ).hexdigest()[:10].upper()

            candidate = (
                f"EVIDENCE_{type_prefix}_{digest}"
            )

        return candidate

    def parse_many(
        self,
        method_type: AssessmentMethodType | str,
        values: Iterable[object],
    ) -> List[AssessmentMethod]:
        return [
            self.parse(
                method_type,
                value,
            )
            for value in values
        ]

    def _parse_object(
        self,
        token: str,
        method_type: AssessmentMethodType,
    ) -> AssessmentObject:
        object_type = self.classify(
            token,
            method_type,
        )

        title = self.normalize_title(
            token
        )

        canonical_id = self.canonical_id(
            token,
            object_type,
        )

        return AssessmentObject(
            canonical_id=canonical_id,
            object_type=object_type,
            title=title,
            raw_text=token,
        )

    @staticmethod
    def _coerce_method_type(
        value: AssessmentMethodType | str,
    ) -> AssessmentMethodType:
        if isinstance(
            value,
            AssessmentMethodType,
        ):
            return value

        text = str(value).strip()

        for item in AssessmentMethodType:
            if (
                item.value.casefold()
                == text.casefold()
            ):
                return item

        raise AssessmentMethodParserError(
            "Unknown assessment method type: "
            f"{value!r}"
        )

    def _strip_selection_wrapper(
        self,
        value: str,
    ) -> str:
        result = value.strip()

        upper = result.upper()

        for marker in self._SELECTION_MARKERS:
            marker_upper = marker.upper()

            if marker_upper in upper:
                index = upper.find(
                    marker_upper
                )

                result = result[
                    index + len(marker):
                ]

                break

        result = result.strip()

        # Remove common closing bracket left by
        # "[SELECT FROM: ... ]".
        if result.endswith("]"):
            result = result[:-1].rstrip()

        return result

    @staticmethod
    def _clean_token(
        value: str,
    ) -> str:
        result = value.strip()

        result = re.sub(
            r"^[\-\–\—\*\u2022]+\s*",
            "",
            result,
        )

        result = re.sub(
            r"\s+",
            " ",
            result,
        )

        result = result.strip(
            " \t.;,"
        )

        return result

    @staticmethod
    def _normalize_phrase(
        value: str,
    ) -> str:
        result = value.strip().casefold()

        result = result.replace(
            "&",
            " and ",
        )

        result = re.sub(
            r"[-_/]+",
            " ",
            result,
        )

        result = re.sub(
            r"[^\w\s]",
            " ",
            result,
        )

        result = re.sub(
            r"\s+",
            " ",
            result,
        )

        return result.strip()

    @staticmethod
    def _title_case(
        value: str,
    ) -> str:
        small_words = {
            "a",
            "an",
            "and",
            "as",
            "at",
            "by",
            "for",
            "from",
            "in",
            "of",
            "on",
            "or",
            "the",
            "to",
            "with",
        }

        words = value.split()

        result: List[str] = []

        for index, word in enumerate(
            words
        ):
            if (
                index > 0
                and word in small_words
            ):
                result.append(word)
            else:
                result.append(
                    word.capitalize()
                )

        return " ".join(result)

    @staticmethod
    def _semantic_tokens(
        value: str,
    ) -> List[str]:
        normalized = re.sub(
            r"[^A-Za-z0-9]+",
            " ",
            value,
        ).upper()

        stop_words = {
            "A",
            "AN",
            "AND",
            "ASSOCIATED",
            "FOR",
            "OF",
            "THE",
            "TO",
            "WITH",
        }

        tokens = [
            token
            for token in normalized.split()
            if token
            and token not in stop_words
        ]

        return tokens

    @staticmethod
    def _type_prefix(
        object_type: AssessmentObjectType,
    ) -> str:
        mapping = {
            AssessmentObjectType.POLICY:
                "POLICY",

            AssessmentObjectType.PROCEDURE:
                "PROCEDURE",

            AssessmentObjectType.PLAN:
                "PLAN",

            AssessmentObjectType.SYSTEM_SECURITY_PLAN:
                "SSP",

            AssessmentObjectType.CONFIGURATION:
                "CONFIGURATION",

            AssessmentObjectType.CONFIGURATION_BASELINE:
                "CONFIGURATION_BASELINE",

            AssessmentObjectType.SCREENSHOT:
                "SCREENSHOT",

            AssessmentObjectType.LOG:
                "LOG",

            AssessmentObjectType.REPORT:
                "REPORT",

            AssessmentObjectType.RECORD:
                "RECORD",

            AssessmentObjectType.INVENTORY:
                "INVENTORY",

            AssessmentObjectType.DIAGRAM:
                "DIAGRAM",

            AssessmentObjectType.CONTRACT:
                "CONTRACT",

            AssessmentObjectType.AGREEMENT:
                "AGREEMENT",

            AssessmentObjectType.INTERCONNECTION:
                "INTERCONNECTION",

            AssessmentObjectType.PERSONNEL_RECORD:
                "PERSONNEL_RECORD",

            AssessmentObjectType.TRAINING_RECORD:
                "TRAINING_RECORD",

            AssessmentObjectType.RISK_ASSESSMENT:
                "RISK_ASSESSMENT",

            AssessmentObjectType.SECURITY_ASSESSMENT:
                "SECURITY_ASSESSMENT",

            AssessmentObjectType.POAM:
                "POAM",

            AssessmentObjectType.INTERVIEW_SUBJECT:
                "INTERVIEW",

            AssessmentObjectType.TEST_TARGET:
                "TEST",

            AssessmentObjectType.TECHNICAL_EVIDENCE:
                "TECHNICAL",

            AssessmentObjectType.OTHER:
                "OTHER",
        }

        return mapping[
            object_type
        ]

    @staticmethod
    def _deduplicate_objects(
        objects: Iterable[AssessmentObject],
    ) -> tuple[AssessmentObject, ...]:
        result: List[
            AssessmentObject
        ] = []

        seen = set()

        for item in objects:
            if item.canonical_id in seen:
                continue

            seen.add(
                item.canonical_id
            )

            result.append(item)

        return tuple(result)