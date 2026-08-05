from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


class POAMTrackerError(Exception):
    """Raised when POA&M synchronization fails."""


@dataclass
class POAMEntry:
    poam_id: str
    requirement_id: str
    title: str
    domain: str
    status: str = "Open"
    owner: str = ""
    corrective_action: str = ""
    milestone: str = ""


class POAMTracker:
    """
    Synchronizes NOT MET assessment requirements with
    the POA&M worksheet.
    """

    def __init__(self) -> None:
        self._entries: Dict[str, POAMEntry] = {}

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def entries(self) -> List[POAMEntry]:
        return list(self._entries.values())

    def synchronize(
        self,
        assessment_rows: List[Dict],
    ) -> List[POAMEntry]:
        """
        Synchronize Assessment rows into POA&M entries.

        assessment_rows example:

        {
            "requirement_id": "...",
            "title": "...",
            "domain": "...",
            "status": "MET"
        }
        """

        active_requirements = set()

        for row in assessment_rows:

            requirement_id = row["requirement_id"]
            status = row["status"]

            if status != "NOT MET":
                continue

            active_requirements.add(requirement_id)

            if requirement_id not in self._entries:

                self._entries[
                    requirement_id
                ] = self._create_entry(row)

        obsolete = [
            requirement
            for requirement in self._entries
            if requirement not in active_requirements
        ]

        for requirement in obsolete:
            del self._entries[requirement]

        return self.entries()

    def find(
        self,
        requirement_id: str,
    ) -> Optional[POAMEntry]:
        return self._entries.get(
            requirement_id
        )

    def _create_entry(
        self,
        assessment_row: Dict,
    ) -> POAMEntry:

        requirement_id = assessment_row[
            "requirement_id"
        ]

        return POAMEntry(
            poam_id=self._next_poam_id(),
            requirement_id=requirement_id,
            title=assessment_row["title"],
            domain=assessment_row["domain"],
        )

    def _next_poam_id(
        self,
    ) -> str:

        next_number = (
            len(self._entries) + 1
        )

        return f"POAM-{next_number:04d}"