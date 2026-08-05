from __future__ import annotations

import pytest

from src.workbook.poam_tracker import (
    POAMEntry,
    POAMTracker,
)


@pytest.fixture
def tracker() -> POAMTracker:
    return POAMTracker()


def test_new_tracker_is_empty(
    tracker: POAMTracker,
) -> None:
    assert tracker.entry_count == 0
    assert tracker.entries() == []


def test_synchronize_creates_entry_for_not_met_requirement(
    tracker: POAMTracker,
) -> None:
    rows = [
        {
            "requirement_id": "AC.L2-3.1.1",
            "title": "Authorized Access Control",
            "domain": "AC",
            "status": "NOT MET",
        }
    ]

    entries = tracker.synchronize(rows)

    assert len(entries) == 1
    assert tracker.entry_count == 1

    entry = entries[0]

    assert entry.poam_id == "POAM-0001"
    assert entry.requirement_id == "AC.L2-3.1.1"
    assert entry.title == "Authorized Access Control"
    assert entry.domain == "AC"
    assert entry.status == "Open"


def test_met_requirement_does_not_create_entry(
    tracker: POAMTracker,
) -> None:
    rows = [
        {
            "requirement_id": "AC.L2-3.1.1",
            "title": "Authorized Access Control",
            "domain": "AC",
            "status": "MET",
        }
    ]

    entries = tracker.synchronize(rows)

    assert entries == []
    assert tracker.entry_count == 0


def test_not_assessed_requirement_does_not_create_entry(
    tracker: POAMTracker,
) -> None:
    rows = [
        {
            "requirement_id": "AC.L2-3.1.1",
            "title": "Authorized Access Control",
            "domain": "AC",
            "status": "NOT ASSESSED",
        }
    ]

    entries = tracker.synchronize(rows)

    assert entries == []
    assert tracker.entry_count == 0


def test_multiple_not_met_requirements_create_multiple_entries(
    tracker: POAMTracker,
) -> None:
    rows = [
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
            "status": "NOT MET",
        },
    ]

    entries = tracker.synchronize(rows)

    assert len(entries) == 2

    assert [
        entry.poam_id
        for entry in entries
    ] == [
        "POAM-0001",
        "POAM-0002",
    ]


def test_duplicate_requirement_does_not_create_duplicate_entry(
    tracker: POAMTracker,
) -> None:
    row = {
        "requirement_id": "AC.L2-3.1.1",
        "title": "Authorized Access Control",
        "domain": "AC",
        "status": "NOT MET",
    }

    tracker.synchronize([row])
    tracker.synchronize([row])

    assert tracker.entry_count == 1


def test_find_returns_existing_entry(
    tracker: POAMTracker,
) -> None:
    tracker.synchronize(
        [
            {
                "requirement_id": "AC.L2-3.1.1",
                "title": "Authorized Access Control",
                "domain": "AC",
                "status": "NOT MET",
            }
        ]
    )

    entry = tracker.find("AC.L2-3.1.1")

    assert entry is not None
    assert entry.requirement_id == "AC.L2-3.1.1"


def test_find_returns_none_for_unknown_requirement(
    tracker: POAMTracker,
) -> None:
    assert tracker.find("XX.L2-3.99.99") is None


def test_existing_entry_is_preserved_during_resynchronization(
    tracker: POAMTracker,
) -> None:
    row = {
        "requirement_id": "AC.L2-3.1.1",
        "title": "Authorized Access Control",
        "domain": "AC",
        "status": "NOT MET",
    }

    tracker.synchronize([row])

    entry = tracker.find("AC.L2-3.1.1")

    assert entry is not None

    entry.owner = "Security Manager"
    entry.corrective_action = "Implement access review process."
    entry.milestone = "Complete account inventory."

    tracker.synchronize([row])

    updated = tracker.find("AC.L2-3.1.1")

    assert updated is entry
    assert updated.owner == "Security Manager"
    assert (
        updated.corrective_action
        == "Implement access review process."
    )
    assert updated.milestone == "Complete account inventory."


def test_entry_removed_when_requirement_is_no_longer_not_met(
    tracker: POAMTracker,
) -> None:
    tracker.synchronize(
        [
            {
                "requirement_id": "AC.L2-3.1.1",
                "title": "Authorized Access Control",
                "domain": "AC",
                "status": "NOT MET",
            }
        ]
    )

    tracker.synchronize(
        [
            {
                "requirement_id": "AC.L2-3.1.1",
                "title": "Authorized Access Control",
                "domain": "AC",
                "status": "MET",
            }
        ]
    )

    assert tracker.entry_count == 0
    assert tracker.find("AC.L2-3.1.1") is None


def test_only_obsolete_entries_are_removed(
    tracker: POAMTracker,
) -> None:
    initial_rows = [
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
            "status": "NOT MET",
        },
    ]

    tracker.synchronize(initial_rows)

    tracker.synchronize(
        [
            {
                "requirement_id": "AC.L2-3.1.1",
                "title": "Authorized Access Control",
                "domain": "AC",
                "status": "MET",
            },
            {
                "requirement_id": "AU.L2-3.3.1",
                "title": "System Auditing",
                "domain": "AU",
                "status": "NOT MET",
            },
        ]
    )

    assert tracker.entry_count == 1
    assert tracker.find("AC.L2-3.1.1") is None
    assert tracker.find("AU.L2-3.3.1") is not None


def test_entries_returns_poam_entry_objects(
    tracker: POAMTracker,
) -> None:
    tracker.synchronize(
        [
            {
                "requirement_id": "AC.L2-3.1.1",
                "title": "Authorized Access Control",
                "domain": "AC",
                "status": "NOT MET",
            }
        ]
    )

    entries = tracker.entries()

    assert all(
        isinstance(entry, POAMEntry)
        for entry in entries
    )


def test_default_remediation_fields_are_blank(
    tracker: POAMTracker,
) -> None:
    tracker.synchronize(
        [
            {
                "requirement_id": "AC.L2-3.1.1",
                "title": "Authorized Access Control",
                "domain": "AC",
                "status": "NOT MET",
            }
        ]
    )

    entry = tracker.find("AC.L2-3.1.1")

    assert entry is not None
    assert entry.owner == ""
    assert entry.corrective_action == ""
    assert entry.milestone == ""


def test_incremental_sync_assigns_next_poam_id(
    tracker: POAMTracker,
) -> None:
    tracker.synchronize(
        [
            {
                "requirement_id": "AC.L2-3.1.1",
                "title": "Authorized Access Control",
                "domain": "AC",
                "status": "NOT MET",
            }
        ]
    )

    entries = tracker.synchronize(
        [
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
                "status": "NOT MET",
            },
        ]
    )

    entry_map = {
        entry.requirement_id: entry
        for entry in entries
    }

    assert (
        entry_map["AC.L2-3.1.1"].poam_id
        == "POAM-0001"
    )
    assert (
        entry_map["AU.L2-3.3.1"].poam_id
        == "POAM-0002"
    )


def test_empty_synchronization_removes_all_entries(
    tracker: POAMTracker,
) -> None:
    tracker.synchronize(
        [
            {
                "requirement_id": "AC.L2-3.1.1",
                "title": "Authorized Access Control",
                "domain": "AC",
                "status": "NOT MET",
            }
        ]
    )

    tracker.synchronize([])

    assert tracker.entry_count == 0
    assert tracker.entries() == []