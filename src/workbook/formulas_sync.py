from __future__ import annotations

from dataclasses import dataclass

from openpyxl.worksheet.worksheet import Worksheet


class FormulaSyncError(Exception):
    """Raised when workbook formulas cannot be synchronized."""


@dataclass(frozen=True)
class FormulaSyncResult:
    assessment_rows_updated: int
    poam_rows_updated: int
    dashboard_updated: bool


class FormulaSynchronizer:
    """
    Restores calculated formulas after workbook synchronization.

    This class intentionally contains only Excel formula logic.
    """

    ASSESSMENT_FIRST_ROW = 6
    POAM_FIRST_ROW = 6
    MAX_REQUIREMENTS = 110
    MAX_POAM_ROWS = 300

    def synchronize(
        self,
        assessment_sheet: Worksheet,
        poam_sheet: Worksheet,
        dashboard_sheet: Worksheet | None = None,
    ) -> FormulaSyncResult:

        assessment_count = self._update_assessment(
            assessment_sheet
        )

        poam_count = self._update_poam(
            poam_sheet
        )

        dashboard_updated = False

        if dashboard_sheet is not None:
            self._update_dashboard(
                dashboard_sheet
            )
            dashboard_updated = True

        return FormulaSyncResult(
            assessment_rows_updated=assessment_count,
            poam_rows_updated=poam_count,
            dashboard_updated=dashboard_updated,
        )

    def _update_assessment(
        self,
        worksheet: Worksheet,
    ) -> int:

        updated = 0

        for row in range(
            self.ASSESSMENT_FIRST_ROW,
            self.ASSESSMENT_FIRST_ROW
            + self.MAX_REQUIREMENTS,
        ):

            requirement = worksheet[
                f"B{row}"
            ].value

            if requirement in {
                None,
                "",
            }:
                break

            worksheet[
                f"N{row}"
            ] = self._assessment_formula(
                row
            )

            updated += 1

        return updated

    def _update_poam(
        self,
        worksheet: Worksheet,
    ) -> int:

        updated = 0

        for row in range(
            self.POAM_FIRST_ROW,
            self.POAM_FIRST_ROW
            + self.MAX_POAM_ROWS,
        ):

            poam_id = worksheet[
                f"A{row}"
            ].value

            if poam_id in {
                None,
                "",
            }:
                continue

            worksheet[
                f"N{row}"
            ] = self._risk_formula(
                row
            )

            worksheet[
                f"R{row}"
            ] = self._days_open_formula(
                row
            )

            worksheet[
                f"S{row}"
            ] = self._aging_formula(
                row
            )

            updated += 1

        return updated

    def _update_dashboard(
        self,
        worksheet: Worksheet,
    ) -> None:

        #
        # Placeholder.
        #
        # Later sprints will populate live dashboard
        # formulas and named ranges.
        #
        worksheet["B2"] = "=TODAY()"

    @staticmethod
    def _assessment_formula(
    row: int,
    ) -> str:
        return (
        f'=IF(OR('
        f'I{row}="MET",'
        f'I{row}="NOT APPLICABLE",'
        f'I{row}="NOT ASSESSED"),'
        f'0,'
        f'IF(AND('
        f'K{row}="Yes",'
        f'J{row}="PARTIALLY IMPLEMENTED"),'
        f'3,'
        f'L{row}))'
    )

    @staticmethod
    def _risk_formula(
        row: int,
    ) -> str:

        return (
            f'=IF(OR(L{row}="",M{row}=""),"",'
            f'IF(L{row}="Critical",4,'
            f'IF(L{row}="High",3,'
            f'IF(L{row}="Medium",2,1)))'
            f'*'
            f'IF(M{row}="Almost Certain",5,'
            f'IF(M{row}="Likely",4,'
            f'IF(M{row}="Possible",3,'
            f'IF(M{row}="Unlikely",2,1)))))'
        )

    @staticmethod
    def _days_open_formula(
        row: int,
    ) -> str:

        return (
            f'=IF(O{row}="","",'
            f'IF(Q{row}<>"",'
            f'Q{row}-O{row},'
            f'TODAY()-O{row}))'
        )

    @staticmethod
    def _aging_formula(
        row: int,
    ) -> str:

        return (
            f'=IF(R{row}="","",'
            f'IF(R{row}<=30,"0-30 Days",'
            f'IF(R{row}<=60,"31-60 Days",'
            f'IF(R{row}<=90,"61-90 Days",'
            f'IF(R{row}<=180,'
            f'"91-180 Days","181+ Days")))))'
        )