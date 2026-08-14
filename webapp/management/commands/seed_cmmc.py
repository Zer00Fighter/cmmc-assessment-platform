from __future__ import annotations

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from webapp.models import (
    AssessmentObjective, AssessmentProcedure, Framework, ObjectiveAssessment, Requirement,
)


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
        objectives_path = root / "data" / "controls" / "cmmc_level2_objectives.csv"
        objective_count = 0
        with objectives_path.open(encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                requirement = Requirement.objects.get(
                    framework=framework, requirement_id=row["requirement_id"].strip().upper()
                )
                AssessmentObjective.objects.update_or_create(
                    requirement=requirement, objective_id=row["objective_id"].strip(),
                    defaults={
                        "text": row["objective_text"],
                        "source_document": row["source_document"],
                        "source_version": row["source_version"],
                        "source_page_start": int(row["source_page_start"]),
                        "source_page_end": int(row["source_page_end"]),
                    },
                )
                objective_count += 1
        methods_path = root / "data" / "mappings" / "assessment_methods.csv"
        procedure_count = 0
        with methods_path.open(encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                requirement = Requirement.objects.get(
                    framework=framework, requirement_id=row["requirement_id"].strip().upper()
                )
                AssessmentProcedure.objects.update_or_create(
                    requirement=requirement, objective=None,
                    method=row["method"].strip().upper(),
                    sequence=int(row["object_sequence"]),
                    defaults={
                        "assessment_object": row["assessment_object"],
                        "source_page_start": int(row["source_page_start"]),
                        "source_page_end": int(row["source_page_end"]),
                    },
                )
                procedure_count += 1
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {objective_count} objectives and {procedure_count} procedures."
        ))
        hydrated = 0
        for result in framework.requirements.prefetch_related("objectives").all():
            for control_result in result.assessment_results.all():
                for objective in result.objectives.all():
                    _, created = ObjectiveAssessment.objects.get_or_create(
                        control_result=control_result, objective=objective
                    )
                    hydrated += int(created)
        self.stdout.write(self.style.SUCCESS(
            f"Created {hydrated} missing objective assessment results."
        ))
