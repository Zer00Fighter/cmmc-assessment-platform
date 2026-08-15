from __future__ import annotations

import hashlib
import json

from django.db import transaction
from django.utils import timezone

from .models import AssessmentBaseline, ControlAssessment, EvidenceArtifact


def _digest(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def baseline_checksum(snapshot: dict) -> str:
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def assessment_snapshot(assessment) -> dict:
    controls = {}
    results = assessment.control_results.select_related(
        "requirement__framework"
    ).prefetch_related("evidence_artifacts")
    for result in results:
        key = f"{result.requirement.framework.code}::{result.requirement.requirement_id}"
        artifacts = list(result.evidence_artifacts.all())
        controls[key] = {
            "framework": result.requirement.framework.code,
            "requirement_id": result.requirement.requirement_id,
            "title": result.requirement.title,
            "domain": result.requirement.domain,
            "status": result.status,
            "implementation_state": result.implementation_state,
            "deduction": result.calculated_deduction,
            "finding_digest": _digest(result.assessor_notes_findings),
            "has_finding": bool(result.assessor_notes_findings.strip()),
            "evidence_count": len(artifacts),
            "accepted_evidence_count": sum(
                item.review_status == EvidenceArtifact.ReviewStatus.ACCEPTED
                for item in artifacts
            ),
        }
    framework_scores = {}
    for framework in assessment.frameworks.all():
        framework_results = assessment.control_results.filter(requirement__framework=framework)
        score = None
        if framework.maximum_score is not None:
            score = framework.maximum_score - sum(
                framework_results.values_list("calculated_deduction", flat=True)
            )
        framework_scores[framework.code] = score
    return {
        "schema_version": 1,
        "assessment_id": assessment.id,
        "assessment_name": assessment.name,
        "system_id": assessment.system_id,
        "organization_id": assessment.system.organization_id,
        "status": assessment.status,
        "signed_off_at": assessment.signed_off_at.isoformat() if assessment.signed_off_at else "",
        "framework_scores": framework_scores,
        "controls": controls,
    }


@transaction.atomic
def create_baseline(*, assessment, name: str, description: str, actor) -> AssessmentBaseline:
    if (not assessment.locked or assessment.quality_review_status != "APPROVED"
            or not assessment.signed_off_at):
        raise ValueError("Only a signed-off assessment with approved quality review can be baselined.")
    snapshot = assessment_snapshot(assessment)
    return AssessmentBaseline.objects.create(
        assessment=assessment, name=name, description=description,
        snapshot=snapshot, checksum=baseline_checksum(snapshot), created_by=actor,
    )


@transaction.atomic
def approve_baseline(baseline: AssessmentBaseline, actor) -> None:
    if baseline.status != AssessmentBaseline.Status.DRAFT:
        raise ValueError("Only a draft baseline can be approved.")
    if baseline.checksum != baseline_checksum(baseline.snapshot):
        raise ValueError("The baseline snapshot failed its integrity check.")
    baseline.status = AssessmentBaseline.Status.APPROVED
    baseline.approved_by = actor
    baseline.approved_at = timezone.now()
    baseline.save(update_fields=("status", "approved_by", "approved_at"))


def compare_to_baseline(assessment, baseline: AssessmentBaseline) -> dict:
    if baseline.status != AssessmentBaseline.Status.APPROVED:
        raise ValueError("Comparisons require an approved baseline.")
    if baseline.assessment.system_id != assessment.system_id:
        raise ValueError("The baseline belongs to a different system.")
    if baseline.checksum != baseline_checksum(baseline.snapshot):
        raise ValueError("The baseline snapshot failed its integrity check.")
    current = assessment_snapshot(assessment)
    prior_controls = baseline.snapshot.get("controls", {})
    current_controls = current["controls"]
    rows = []
    counts = {key: 0 for key in ("IMPROVED", "REGRESSED", "CHANGED", "UNCHANGED", "NEW", "REMOVED")}
    for key in sorted(set(prior_controls) | set(current_controls)):
        before, after = prior_controls.get(key), current_controls.get(key)
        if before is None:
            change = "NEW"
        elif after is None:
            change = "REMOVED"
        elif before["status"] == after["status"]:
            change = "UNCHANGED"
        elif before["status"] == ControlAssessment.Status.NOT_MET and after["status"] == ControlAssessment.Status.MET:
            change = "IMPROVED"
        elif before["status"] == ControlAssessment.Status.MET and after["status"] == ControlAssessment.Status.NOT_MET:
            change = "REGRESSED"
        elif before["status"] == ControlAssessment.Status.NOT_ASSESSED and after["status"] != ControlAssessment.Status.NOT_ASSESSED:
            change = "IMPROVED"
        else:
            change = "CHANGED"
        counts[change] += 1
        reference = after or before
        rows.append({
            "key": key, "framework": reference["framework"],
            "requirement_id": reference["requirement_id"], "title": reference["title"],
            "before_status": before["status"] if before else "—",
            "after_status": after["status"] if after else "—", "change": change,
            "finding_changed": bool(before and after and before["finding_digest"] != after["finding_digest"]),
            "evidence_delta": ((after or {}).get("accepted_evidence_count", 0)
                               - (before or {}).get("accepted_evidence_count", 0)),
        })
    score_deltas = []
    prior_scores = baseline.snapshot.get("framework_scores", {})
    for code in sorted(set(prior_scores) | set(current["framework_scores"])):
        before, after = prior_scores.get(code), current["framework_scores"].get(code)
        score_deltas.append({
            "framework": code, "before": before, "after": after,
            "delta": after - before if before is not None and after is not None else None,
        })
    return {"counts": counts, "rows": rows, "score_deltas": score_deltas,
            "baseline": baseline, "current": current}
