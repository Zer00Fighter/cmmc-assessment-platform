from __future__ import annotations

from src.workbook.workbook_sync import (
    WorkbookSynchronizer,
    WorkbookSyncResult,
)


def sample_rows():
    return [
        {
            "requirement_id": "AC.L2-3.1.1",
            "title": "Authorized Access Control",
            "domain": "AC",
            "status": "NOT MET",
        },
        {
            "requirement_id": "AU.L2-3.3.1",
            "title": "System Auditing",
            "domain": "AU",
            "status": "MET",
        },
    ]


def test_new_synchronizer_is_empty() -> None:
    synchronizer = WorkbookSynchronizer()

    assert synchronizer.poam == []


def test_empty_synchronization() -> None:
    synchronizer = WorkbookSynchronizer()

    result = synchronizer.synchronize([])

    assert isinstance(
        result,
        WorkbookSyncResult,
    )

    assert result.assessment_rows == 0
    assert result.poam_entries == 0
    assert result.evidence_entries == 0
    assert result.dashboard_updated is True


def test_synchronization_counts_rows() -> None:
    synchronizer = WorkbookSynchronizer()

    result = synchronizer.synchronize(
        sample_rows()
    )

    assert result.assessment_rows == 2


def test_not_met_creates_poam() -> None:
    synchronizer = WorkbookSynchronizer()

    synchronizer.synchronize(
        sample_rows()
    )

    assert len(
        synchronizer.poam
    ) == 1

    assert (
        synchronizer.poam[0].requirement_id
        == "AC.L2-3.1.1"
    )


def test_dashboard_flag_is_true() -> None:
    synchronizer = WorkbookSynchronizer()

    result = synchronizer.synchronize(
        sample_rows()
    )

    assert result.dashboard_updated is True


def test_result_contains_expected_counts() -> None:
    synchronizer = WorkbookSynchronizer()

    result = synchronizer.synchronize(
        sample_rows()
    )

    assert result.poam_entries == 1
    assert result.evidence_entries == 0


def test_multiple_synchronizations_are_idempotent() -> None:
    synchronizer = WorkbookSynchronizer()

    synchronizer.synchronize(
        sample_rows()
    )

    synchronizer.synchronize(
        sample_rows()
    )

    assert len(
        synchronizer.poam
    ) == 1


def test_poam_property_returns_live_entries() -> None:
    synchronizer = WorkbookSynchronizer()

    synchronizer.synchronize(
        sample_rows()
    )

    poam = synchronizer.poam

    assert len(poam) == 1

    assert poam[0].poam_id == (
        "POAM-0001"
    )


def test_requirement_removed_when_met() -> None:
    synchronizer = WorkbookSynchronizer()

    synchronizer.synchronize(
        sample_rows()
    )

    synchronizer.synchronize(
        [
            {
                "requirement_id": "AC.L2-3.1.1",
                "title": "Authorized Access Control",
                "domain": "AC",
                "status": "MET",
            }
        ]
    )

    assert synchronizer.poam == []


def test_multiple_not_met_requirements() -> None:
    synchronizer = WorkbookSynchronizer()

    result = synchronizer.synchronize(
        [
            {
                "requirement_id": "AC.L2-3.1.1",
                "title": "Access",
                "domain": "AC",
                "status": "NOT MET",
            },
            {
                "requirement_id": "AU.L2-3.3.1",
                "title": "Audit",
                "domain": "AU",
                "status": "NOT MET",
            },
            {
                "requirement_id": "IA.L2-3.5.1",
                "title": "Identity",
                "domain": "IA",
                "status": "MET",
            },
        ]
    )

    assert result.poam_entries == 2

    ids = {
        entry.requirement_id
        for entry in synchronizer.poam
    }

    assert ids == {
        "AC.L2-3.1.1",
        "AU.L2-3.3.1",
    }


def test_poam_entries_preserve_tracker_state() -> None:
    synchronizer = WorkbookSynchronizer()

    synchronizer.synchronize(
        sample_rows()
    )

    synchronizer.poam[0].owner = (
        "Security Manager"
    )

    synchronizer.synchronize(
        sample_rows()
    )

    assert (
        synchronizer.poam[0].owner
        == "Security Manager"
    )