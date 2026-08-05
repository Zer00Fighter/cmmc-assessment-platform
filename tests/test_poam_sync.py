from __future__ import annotations

from openpyxl import Workbook

from src.workbook.assessment_sync import AssessmentRecord
from src.workbook.poam_sync import (
    POAMWorksheetSynchronizer,
    POAMSyncError,
)


def make_record(
    requirement_id: str,
    status: str = "NOT MET",
    owner: str = "",
) -> AssessmentRecord:
    return AssessmentRecord(
        requirement_id=requirement_id,
        title=f"Requirement {requirement_id}",
        domain=requirement_id.split(".")[0],
        status=status,
        implementation_state="",
        applicable=True,
        owner=owner,
        evidence_status="",
        row_number=6,
    )


def build_poam_sheet():
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "POA&M"
    return worksheet


def test_sync_creates_new_entry() -> None:
    worksheet = build_poam_sheet()

    synchronizer = POAMWorksheetSynchronizer()

    result = synchronizer.synchronize(
        worksheet,
        [
            make_record("AC.L2-3.1.1"),
        ],
    )

    assert result.created_count == 1
    assert worksheet["A6"].value == "POAM-0001"
    assert worksheet["B6"].value == "AC.L2-3.1.1"
    assert worksheet["C6"].value == "Requirement AC.L2-3.1.1"
    assert worksheet["D6"].value == "AC"


def test_existing_row_is_updated_not_recreated() -> None:
    worksheet = build_poam_sheet()

    worksheet["A6"] = "POAM-0001"
    worksheet["B6"] = "AC.L2-3.1.1"
    worksheet["E6"] = "Existing weakness"

    synchronizer = POAMWorksheetSynchronizer()

    result = synchronizer.synchronize(
        worksheet,
        [
            make_record("AC.L2-3.1.1"),
        ],
    )

    assert result.updated_count == 1
    assert worksheet["E6"].value == "Existing weakness"


def test_duplicate_requirement_rows_raise_error() -> None:
    worksheet = build_poam_sheet()

    worksheet["B6"] = "AC.L2-3.1.1"
    worksheet["B7"] = "AC.L2-3.1.1"

    synchronizer = POAMWorksheetSynchronizer()

    try:
        synchronizer.synchronize(
            worksheet,
            [make_record("AC.L2-3.1.1")],
        )
        assert False
    except POAMSyncError:
        pass


def test_met_requirement_creates_no_entry() -> None:
    worksheet = build_poam_sheet()

    synchronizer = POAMWorksheetSynchronizer()

    result = synchronizer.synchronize(
        worksheet,
        [
            make_record(
                "AC.L2-3.1.1",
                status="MET",
            )
        ],
    )

    assert result.final_poam_count == 0


def test_multiple_not_met_entries() -> None:
    worksheet = build_poam_sheet()

    synchronizer = POAMWorksheetSynchronizer()

    result = synchronizer.synchronize(
        worksheet,
        [
            make_record("AC.L2-3.1.1"),
            make_record("AU.L2-3.3.1"),
            make_record(
                "IA.L2-3.5.1",
                status="MET",
            ),
        ],
    )

    assert result.final_poam_count == 2

    assert worksheet["B6"].value == "AC.L2-3.1.1"
    assert worksheet["B7"].value == "AU.L2-3.3.1"


def test_owner_is_written() -> None:
    worksheet = build_poam_sheet()

    synchronizer = POAMWorksheetSynchronizer()

    synchronizer.synchronize(
        worksheet,
        [
            make_record(
                "AC.L2-3.1.1",
                owner="Security Manager",
            )
        ],
    )

    assert worksheet["I6"].value == "Security Manager"


def test_user_owner_is_preserved() -> None:
    worksheet = build_poam_sheet()

    worksheet["A6"] = "POAM-0001"
    worksheet["B6"] = "AC.L2-3.1.1"
    worksheet["I6"] = "CISO"

    synchronizer = POAMWorksheetSynchronizer()

    synchronizer.synchronize(
        worksheet,
        [
            make_record(
                "AC.L2-3.1.1",
                owner="Security Manager",
            )
        ],
    )

    assert worksheet["I6"].value == "CISO"


def test_obsolete_entry_is_cleared() -> None:
    worksheet = build_poam_sheet()

    worksheet["A6"] = "POAM-0001"
    worksheet["B6"] = "AC.L2-3.1.1"

    synchronizer = POAMWorksheetSynchronizer()

    result = synchronizer.synchronize(
        worksheet,
        [],
    )

    assert result.cleared_count == 1
    assert worksheet["B6"].value == ""


def test_formulas_are_restored() -> None:
    worksheet = build_poam_sheet()

    synchronizer = POAMWorksheetSynchronizer()

    synchronizer.synchronize(
        worksheet,
        [
            make_record("AC.L2-3.1.1"),
        ],
    )

    assert worksheet["N6"].value.startswith("=IF(")
    assert worksheet["R6"].value.startswith("=IF(")
    assert worksheet["S6"].value.startswith("=IF(")


def test_requirement_id_normalization() -> None:
    worksheet = build_poam_sheet()

    worksheet["B6"] = "AC-L2-3.1.1"

    synchronizer = POAMWorksheetSynchronizer()

    synchronizer.synchronize(
        worksheet,
        [
            make_record("AC.L2-3.1.1"),
        ],
    )

    assert worksheet["B6"].value == "AC.L2-3.1.1"


def test_created_and_updated_counts() -> None:
    worksheet = build_poam_sheet()

    worksheet["A6"] = "POAM-0001"
    worksheet["B6"] = "AC.L2-3.1.1"

    synchronizer = POAMWorksheetSynchronizer()

    result = synchronizer.synchronize(
        worksheet,
        [
            make_record("AC.L2-3.1.1"),
            make_record("AU.L2-3.3.1"),
        ],
    )

    assert result.updated_count == 1
    assert result.created_count == 1


def test_sync_result_counts() -> None:
    worksheet = build_poam_sheet()

    synchronizer = POAMWorksheetSynchronizer()

    result = synchronizer.synchronize(
        worksheet,
        [
            make_record("AC.L2-3.1.1"),
            make_record("AU.L2-3.3.1"),
        ],
    )

    assert result.assessment_record_count == 2
    assert result.not_met_count == 2
    assert result.final_poam_count == 2