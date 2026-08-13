from __future__ import annotations

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from webapp.models import Framework, Requirement


class Command(BaseCommand):
    help = "Load Omni's CMMC Level 2 framework and requirements"

    def handle(self, *args, **options):
        root = Path(settings.BASE_DIR)
        controls_path = root / "data" / "controls" / "cmmc_level2_controls.csv"
        weights_path = root / "data" / "scoring" / "scoring_weights.csv"
        with weights_path.open(encoding="utf-8-sig", newline="") as source:
            weights = {
                row["requirement_id"].strip().upper(): row
                for row in csv.DictReader(source)
            }
        framework, _ = Framework.objects.update_or_create(
            code="CMMC-L2",
            defaults={
                "name": "CMMC Level 2", "version": "2.13",
                "authority": "U.S. Department of Defense",
                "description": "CMMC Level 2 assessment requirements aligned to NIST SP 800-171.",
                "scoring_method": Framework.ScoringMethod.SPRS,
                "maximum_score": 110, "active": True,
            },
        )
        loaded = 0
        with controls_path.open(encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                requirement_id = row["requirement_id"].strip().upper()
                weight = weights[requirement_id]
                Requirement.objects.update_or_create(
                    framework=framework,
                    requirement_id=requirement_id,
                    defaults={
                        "domain": row["domain_code"],
                        "title": row["title"],
                        "statement": row["statement"],
                        "full_deduction": int(weight["full_deduction_points"]),
                        "partial_credit_allowed": weight["partial_credit_allowed"]
                        .strip()
                        .lower()
                        == "yes",
                    },
                )
                loaded += 1
        self.stdout.write(
            self.style.SUCCESS(f"Loaded {loaded} CMMC Level 2 requirements.")
        )
