from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from src.models.control import Control
from src.models.domain import Domain
from src.models.objective import Objective


def _read_csv(path: Path) -> List[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
    }


def load_domains(path: Path) -> List[Domain]:
    rows = _read_csv(path)

    return [
        Domain(
            code=row["code"].strip(),
            name=row["name"].strip(),
            sequence=int(row["sequence"]),
        )
        for row in rows
    ]


def load_controls(path: Path) -> List[Control]:
    rows = _read_csv(path)

    return [
        Control(
            domain_code=row["domain_code"].strip(),
            requirement_id=row["requirement_id"].strip(),
            title=row["title"].strip(),
            statement=row["statement"].strip(),
            deduction_points=int(row["deduction_points"]),
            poam_eligible=_parse_bool(row["poam_eligible"]),
            source_reference=row.get(
                "source_reference",
                "",
            ).strip(),
        )
        for row in rows
    ]


def load_objectives(path: Path) -> List[Objective]:
    rows = _read_csv(path)

    return [
        Objective(
            requirement_id=row["requirement_id"].strip(),
            objective_id=row["objective_id"].strip(),
            objective_text=row["objective_text"].strip(),
            examine=_parse_bool(row["examine"]),
            interview=_parse_bool(row["interview"]),
            test=_parse_bool(row["test"]),
        )
        for row in rows
    ]


def load_statuses(path: Path) -> List[Dict[str, str]]:
    return _read_csv(path)


def load_scoring_weights(path: Path) -> Dict[str, int]:
    rows = _read_csv(path)

    return {
        row["requirement_id"].strip(): int(
            row["deduction_points"]
        )
        for row in rows
    }