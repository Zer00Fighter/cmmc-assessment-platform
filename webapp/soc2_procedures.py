"""Omni-authored SOC 2 assessment objectives and suggested procedures."""
from __future__ import annotations

from django.db import transaction

from .models import AssessmentObjective, AssessmentProcedure, ObjectiveAssessment, Requirement
from .soc2_activity_import import TSC_FRAMEWORK_CODE

OBJECTIVE_ID = "OMNI-SOC2-CRITERION"
SUGGESTIONS = (
    (AssessmentProcedure.Method.EXAMINE,
     "Examine relevant policies, procedures, configurations, records, and retained evidence supporting this criterion."),
    (AssessmentProcedure.Method.INTERVIEW,
     "Interview responsible personnel to understand control ownership, design, implementation, exceptions, and escalation."),
    (AssessmentProcedure.Method.OBSERVE,
     "Observe the control or supporting process in operation and compare observed behavior with documented expectations."),
    (AssessmentProcedure.Method.TEST,
     "Select appropriate instances or transactions and test whether the control operated as described for the applicable date or period."),
    (AssessmentProcedure.Method.REPERFORM,
     "Independently reperform the control activity or calculation where feasible and compare the result with management's evidence."),
)


@transaction.atomic
def ensure_soc2_execution_catalog() -> dict:
    objectives_created = procedures_created = results_created = 0
    requirements = Requirement.objects.filter(
        framework__code=TSC_FRAMEWORK_CODE
    ).select_related("framework")
    for requirement in requirements:
        objective, created = AssessmentObjective.objects.get_or_create(
            requirement=requirement, objective_id=OBJECTIVE_ID,
            defaults={
                "text": (
                    f"Evaluate the design and implementation of controls supporting "
                    f"{requirement.requirement_id}; for Type II, also evaluate operating "
                    "effectiveness over the examination period."
                ),
                "source_document": "Omni SOC 2 assessment methodology",
                "source_version": "1.0",
            },
        )
        objectives_created += int(created)
        for sequence, (method, text) in enumerate(SUGGESTIONS, 1):
            _, created = AssessmentProcedure.objects.get_or_create(
                requirement=requirement, objective=objective, method=method, sequence=sequence,
                defaults={"assessment_object": text},
            )
            procedures_created += int(created)
        existing_results = set(objective.assessment_results.values_list(
            "control_result_id", flat=True
        ))
        pending = [
            ObjectiveAssessment(control_result=result, objective=objective)
            for result in requirement.assessment_results.all()
            if result.id not in existing_results
        ]
        ObjectiveAssessment.objects.bulk_create(pending, ignore_conflicts=True)
        results_created += len(pending)
    return {
        "requirements": requirements.count(),
        "objectives_created": objectives_created,
        "procedures_created": procedures_created,
        "results_created": results_created,
    }
