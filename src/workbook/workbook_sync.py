from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from src.workbook.poam_tracker import (
    POAMEntry,
    POAMTracker,
)


class WorkbookSyncError(Exception):
    """Raised when workbook synchronization fails."""


@dataclass
class WorkbookSyncResult:
    assessment_rows: int
    poam_entries: int
    evidence_entries: int
    dashboard_updated: bool


class WorkbookSynchronizer:
    """
    Coordinates synchronization between workbook components.

    Responsibilities:
      • Assessment → POA&M
      • Assessment → Evidence
      • Assessment → Dashboard
      • Assessment → Executive Report
      • SSP Crosswalk
    """

    def __init__(self) -> None:
        self.poam_tracker = POAMTracker()

    def synchronize(
        self,
        assessment_rows: List[Dict],
    ) -> WorkbookSyncResult:

        poam_entries = self.poam_tracker.synchronize(
            assessment_rows
        )

        #
        # Phase 2
        # Evidence synchronization
        #

        evidence_count = 0

        #
        # Phase 3
        # Dashboard synchronization
        #

        dashboard_updated = True

        return WorkbookSyncResult(
            assessment_rows=len(
                assessment_rows
            ),
            poam_entries=len(
                poam_entries
            ),
            evidence_entries=evidence_count,
            dashboard_updated=dashboard_updated,
        )

    @property
    def poam(
        self,
    ) -> List[POAMEntry]:
        return self.poam_tracker.entries()