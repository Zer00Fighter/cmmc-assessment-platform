from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from openpyxl import load_workbook

from src.ssp_export import SSPExportMetadata, export_ssp
from src.workbook import WorkbookBuilder

from .models import ControlAssessment, EvidenceArtifact, RemediationPlan
from .remediation_export import build_remediation_workbook


class ReportNotReady(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__("Assessment deliverable is not ready.")


def assessment_readiness(assessment, *, require_template=False) -> dict:
    blockers, warnings = [], []
    organization = assessment.system.organization
    required = {
        "Organization name": organization.name,
        "System name": assessment.system.name,
        "Assessment scope": assessment.system.scope,
        "CAGE code": assessment.system.cage_code,
    }
    for field, value in required.items():
        if not str(value or "").strip():
            blockers.append(f"{field} is missing.")
    results = assessment.control_results.select_related("requirement")
    for result in results:
        control = result.requirement.requirement_id
        if result.status == ControlAssessment.Status.NOT_ASSESSED:
            blockers.append(f"{control} has not been assessed.")
        elif not result.assessor_notes_findings.strip():
            blockers.append(f"{control} requires an Assessor Notes/Findings statement.")
        if not result.ssp_reference.strip():
            warnings.append(f"{control} has no Security Plan reference.")
        if not result.evidence_artifacts.filter(
            review_status=EvidenceArtifact.ReviewStatus.ACCEPTED
        ).exists():
            warnings.append(f"{control} has no accepted supporting artifact.")
    template = Path(settings.OMNI_SSP_TEMPLATE) if settings.OMNI_SSP_TEMPLATE else None
    if require_template and (not template or not template.is_file()):
        blockers.append(
            "Word SSP template is not configured. Set OMNI_SSP_TEMPLATE to the private template path."
        )
    total = results.count()
    assessed = results.exclude(status=ControlAssessment.Status.NOT_ASSESSED).count()
    return {
        "ready": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "total_controls": total,
        "assessed_controls": assessed,
        "completion_percent": round(assessed / total * 100, 2) if total else 0,
    }


def _display_member(membership) -> str:
    if not membership:
        return ""
    return membership.user.get_full_name() or membership.user.username


def build_assessment_workbook(assessment) -> bytes:
    with tempfile.TemporaryDirectory(prefix="omni-report-") as directory:
        path = Path(directory) / "assessment.xlsx"
        WorkbookBuilder(project_root=Path(settings.BASE_DIR), output_path=path).build()
        workbook = load_workbook(path)
        cover = workbook["Cover"]
        cover_values = {
            "Organization Name": assessment.system.organization.name,
            "Assessment Name": assessment.name,
            "Assessment Scope": assessment.system.scope,
            "CAGE Code": assessment.system.cage_code,
            "Assessment Start Date": assessment.created_at.date(),
            "Assessment End Date": timezone.localdate() if assessment.status == "COMPLETE" else "",
            "Lead Assessor": assessment.created_by.get_full_name() or assessment.created_by.username,
        }
        for row in range(1, cover.max_row + 1):
            label = cover.cell(row, 2).value
            if label in cover_values:
                cover.cell(row, 3, cover_values[label])

        results = {
            item.requirement.requirement_id: item
            for item in assessment.control_results.select_related(
                "requirement", "primary_owner__user"
            ).prefetch_related("evidence_artifacts", "remediation_plans")
        }
        sheet = workbook["Assessment"]
        crosswalk = workbook["SSP Crosswalk"]
        for row in range(6, sheet.max_row + 1):
            requirement_id = str(sheet.cell(row, 2).value or "").strip()
            result = results.get(requirement_id)
            if not result:
                continue
            artifacts = list(result.evidence_artifacts.all())
            owner = _display_member(result.primary_owner) or result.control_owner
            sheet.cell(row, 9, result.status)
            sheet.cell(row, 10, result.implementation_state)
            sheet.cell(row, 13, "Yes" if result.calculated_deduction == 3 else "No")
            sheet.cell(row, 14, result.calculated_deduction)
            sheet.cell(row, 15, "Complete" if any(
                item.review_status == EvidenceArtifact.ReviewStatus.ACCEPTED for item in artifacts
            ) else ("In Progress" if artifacts else "Not Started"))
            sheet.cell(row, 16, owner)
            sheet.cell(row, 17, result.ssp_reference)
            sheet.cell(row, 18, result.assessor_notes_findings)
            sheet.cell(row, 19, "Yes" if result.remediation_plans.exclude(
                status__in=(RemediationPlan.Status.CLOSED, RemediationPlan.Status.RISK_ACCEPTED)
            ).exists() else "No")
            evidence_refs = "; ".join(
                f"EA-{item.id:04d} {item.title}" for item in artifacts
            )
            crosswalk.cell(row, 3, result.ssp_reference)
            crosswalk.cell(row, 5, evidence_refs)
            crosswalk.cell(row, 6, owner)
            crosswalk.cell(row, 7, "Mapped" if result.ssp_reference and evidence_refs else (
                "Partially Mapped" if result.ssp_reference or evidence_refs else "Not Mapped"
            ))

        evidence_sheet = workbook["Evidence"]
        artifacts = assessment.evidence_artifacts.select_related("uploaded_by").prefetch_related(
            "controls__requirement"
        )
        for offset, artifact in enumerate(artifacts):
            row = 6 + offset
            controls = ", ".join(
                item.requirement.requirement_id for item in artifact.controls.all()
            )
            location = artifact.external_reference or (artifact.file.name if artifact.file else "")
            values = (
                f"EA-{artifact.id:04d}", artifact.title, "Artifact", artifact.assessor_notes,
                location, artifact.source, "Complete", artifact.get_review_status_display(),
                "", artifact.updated_at.date(), artifact.period_end, controls, "", "Confidential",
                "", artifact.assessor_notes,
            )
            for column, value in enumerate(values, 1):
                evidence_sheet.cell(row, column, value)

        remediation = workbook["POA&M"]
        for row in range(6, remediation.max_row + 1):
            for column in range(1, 25):
                remediation.cell(row, column, "")
        plans = assessment.remediation_plans.prefetch_related(
            "controls__requirement", "milestones__owner__user", "closure_evidence"
        ).select_related("owner__user")
        for offset, plan in enumerate(plans):
            row = 6 + offset
            controls = list(plan.controls.all())
            milestone = plan.milestones.exclude(status="COMPLETE").first() or plan.milestones.first()
            dates_end = plan.actual_completion or timezone.localdate()
            days = max((dates_end - plan.date_identified).days, 0)
            values = (
                plan.remediation_id,
                ", ".join(item.requirement.requirement_id for item in controls),
                "; ".join(item.requirement.title for item in controls),
                ", ".join(sorted({item.requirement.domain for item in controls})),
                plan.weakness_description, plan.root_cause, plan.corrective_action,
                milestone.title if milestone else "", str(milestone.owner) if milestone and milestone.owner else "",
                plan.get_status_display(), plan.get_priority_display(), plan.get_severity_display(),
                plan.get_likelihood_display(), plan.risk_score, plan.date_identified,
                plan.planned_completion, plan.actual_completion, days, "", plan.get_residual_risk_display(),
                plan.get_validation_status_display(),
                ", ".join(f"EA-{item.id:04d}" for item in plan.closure_evidence.all()),
                ", ".join(sorted({item.ssp_reference for item in controls if item.ssp_reference})),
                plan.validation_notes,
            )
            for column, value in enumerate(values, 1):
                remediation.cell(row, column, value)
        workbook.calculation.fullCalcOnLoad = True
        workbook.calculation.forceFullCalc = True
        workbook.save(path)
        return path.read_bytes()


def build_word_ssp(assessment, workbook_bytes: bytes, generated_by) -> bytes:
    readiness = assessment_readiness(assessment, require_template=True)
    if not readiness["ready"]:
        raise ReportNotReady(readiness["blockers"])
    with tempfile.TemporaryDirectory(prefix="omni-ssp-") as directory:
        workbook_path = Path(directory) / "assessment.xlsx"
        output_path = Path(directory) / "ssp.docx"
        workbook_path.write_bytes(workbook_bytes)
        export_ssp(
            settings.OMNI_SSP_TEMPLATE, workbook_path, output_path,
            SSPExportMetadata(
                organization_name=assessment.system.organization.name,
                system_name=assessment.system.name,
                system_owner=assessment.system.system_owner_name,
                prepared_by=generated_by.get_full_name() or generated_by.username,
                version="1.0", export_date=timezone.localdate().isoformat(),
            ),
        )
        return output_path.read_bytes()


def _safe_name(value: str, fallback: str) -> str:
    result = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return result[:120] or fallback


def _artifact_reference_text(artifact) -> str:
    controls = ", ".join(item.requirement.requirement_id for item in artifact.controls.all())
    requests = ", ".join(item.title for item in artifact.requests.all())
    remediation = ", ".join(item.remediation_id for item in artifact.remediation_plans.all())
    registered_by = artifact.uploaded_by.get_full_name() or artifact.uploaded_by.username
    lines = {
        "Artifact ID": f"EA-{artifact.id:04d}", "Title": artifact.title,
        "External URL": artifact.external_reference, "Source": artifact.source,
        "Period Start": artifact.period_start or "", "Period End": artifact.period_end or "",
        "Review Status": artifact.get_review_status_display(),
        "Assessor Notes": artifact.assessor_notes, "Linked Requests": requests,
        "Linked Controls": controls, "Linked Remediation Plans": remediation,
        "Registered At": artifact.created_at.isoformat(), "Registered By": registered_by,
    }
    return "\n".join(f"{key}: {value}" for key, value in lines.items()) + "\n"


def build_package(assessment, generated_by) -> tuple[bytes, dict]:
    readiness = assessment_readiness(assessment, require_template=True)
    if not readiness["ready"]:
        raise ReportNotReady(readiness["blockers"])
    workbook = build_assessment_workbook(assessment)
    ssp = build_word_ssp(assessment, workbook, generated_by)
    remediation = build_remediation_workbook(assessment).getvalue()
    output = io.BytesIO()
    manifest_rows = []
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("Deliverables/Omni-Assessment-Workbook.xlsx", workbook)
        package.writestr("Deliverables/Omni-System-Security-Plan.docx", ssp)
        package.writestr("Deliverables/Omni-Remediation-Action-Plan.xlsx", remediation)
        artifacts = assessment.evidence_artifacts.select_related("uploaded_by").prefetch_related(
            "controls__requirement", "requests", "remediation_plans"
        )
        for artifact in artifacts:
            artifact_id = f"EA-{artifact.id:04d}"
            base = _safe_name(artifact.title, artifact_id)
            controls = ", ".join(item.requirement.requirement_id for item in artifact.controls.all())
            requests = ", ".join(item.title for item in artifact.requests.all())
            remediations = ", ".join(item.remediation_id for item in artifact.remediation_plans.all())
            if artifact.file:
                filename = _safe_name(Path(artifact.file.name).name, f"{artifact_id}.bin")
                with artifact.file.open("rb") as evidence_file:
                    package.writestr(f"Evidence/{artifact_id}_{base}/{filename}", evidence_file.read())
            if artifact.external_reference:
                package.writestr(
                    f"Evidence/{artifact_id}_{base}/{artifact_id}_External_Reference.txt",
                    _artifact_reference_text(artifact),
                )
            manifest_rows.append({
                "artifact_id": artifact_id, "title": artifact.title,
                "review_status": artifact.get_review_status_display(),
                "controls": controls, "requests": requests,
                "remediation_plans": remediations,
                "uploaded_file": Path(artifact.file.name).name if artifact.file else "",
                "external_reference": artifact.external_reference,
            })
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=(
            "artifact_id", "title", "review_status", "controls", "requests",
            "remediation_plans", "uploaded_file", "external_reference",
        ))
        writer.writeheader()
        writer.writerows(manifest_rows)
        package.writestr("Evidence/Evidence-Index.csv", csv_buffer.getvalue())
        package.writestr("Package-Manifest.json", json.dumps({
            "assessment": assessment.name,
            "organization": assessment.system.organization.name,
            "system": assessment.system.name,
            "generated_at": timezone.now().isoformat(),
            "generated_by": generated_by.get_full_name() or generated_by.username,
            "readiness": readiness, "evidence_count": len(manifest_rows),
        }, indent=2))
    return output.getvalue(), readiness


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
