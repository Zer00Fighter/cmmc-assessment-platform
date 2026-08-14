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
from docx import Document

from src.ssp_export import SSPExportMetadata, export_ssp
from src.workbook import WorkbookBuilder

from .models import AuthoritativeDocument, ControlAssessment, EvidenceArtifact, ObjectiveAssessment, RemediationPlan
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
        unassessed_objectives = result.objective_results.filter(
            status="NOT_ASSESSED"
        ).count()
        if unassessed_objectives:
            blockers.append(f"{control} has {unassessed_objectives} unassessed objective(s).")
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


def multi_framework_readiness(assessment) -> dict:
    report = assessment_readiness(assessment)
    for artifact in assessment.evidence_artifacts.all():
        if artifact.freshness in {"EXPIRED", "SUPERSEDED"}:
            report["warnings"].append(f"{artifact.title} is {artifact.freshness.lower()}.")
    for decision in assessment.reuse_decisions.filter(status="APPROVED", reuse_evidence=True):
        if not decision.target_result.evidence_applicability.exists():
            report["blockers"].append(
                f"Reused evidence for {decision.target_result.requirement.requirement_id} needs applicability review."
            )
    report["ready"] = not report["blockers"]
    return report


def build_traceability_csv(assessment) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Framework", "Requirement", "Status", "Mapping basis", "Mapping path",
                     "Evidence", "Evidence applicability", "Testing references", "Finding"])
    decisions = {item.target_result_id: item for item in assessment.reuse_decisions.select_related("target_result")}
    for result in assessment.control_results.select_related("requirement__framework").prefetch_related(
        "evidence_artifacts__applicability_reviews", "objective_results__reused_tests"
    ):
        decision = decisions.get(result.pk)
        evidence = "; ".join(result.evidence_artifacts.values_list("title", flat=True))
        applicability = "; ".join(result.evidence_applicability.values_list("applicability", flat=True))
        tests = sum(item.reused_tests.count() for item in result.objective_results.all())
        writer.writerow([result.requirement.framework.code, result.requirement.requirement_id,
                         result.status, decision.get_basis_display() if decision else "Original",
                         " > ".join(decision.mapping_path) if decision else "", evidence,
                         applicability, tests, result.assessor_notes_findings])
    return output.getvalue().encode("utf-8-sig")


def build_multi_framework_report(assessment, framework=None) -> bytes:
    document = Document()
    title = f"{framework.name} Assessment Report" if framework else "Consolidated Multi-Framework Assessment Report"
    document.add_heading(title, 0)
    document.add_paragraph(f"Organization: {assessment.system.organization.name}")
    document.add_paragraph(f"System: {assessment.system.name}")
    document.add_paragraph(f"Assessment: {assessment.name}")
    selected = [framework] if framework else list(assessment.frameworks.all())
    document.add_heading("Assessment scope and frameworks", level=1)
    document.add_paragraph(assessment.system.scope or "Scope not recorded.")
    document.add_paragraph(", ".join(f"{item.name} {item.version}" for item in selected))
    for item in selected:
        results = assessment.control_results.filter(requirement__framework=item).select_related("requirement")
        document.add_heading(f"{item.name} {item.version}", level=1)
        table = document.add_table(rows=1, cols=5); table.style = "Table Grid"
        for cell, label in zip(table.rows[0].cells, ("Requirement", "Title", "Status", "Evidence", "Conclusion/Finding")):
            cell.text = label
        for result in results:
            cells = table.add_row().cells
            values = (result.requirement.requirement_id, result.requirement.title, result.status,
                      str(result.evidence_artifacts.count()), result.assessor_notes_findings)
            for cell, value in zip(cells, values): cell.text = str(value)
        sources = AuthoritativeDocument.objects.filter(
            authority__canonical_name__iexact=item.name, active=True
        )
        if sources:
            document.add_heading(f"{item.code} authoritative sources", level=2)
            for source in sources:
                document.add_paragraph(f"{source.formal_name} — {source.official_url or 'Source URL pending'}")
    stream = io.BytesIO(); document.save(stream); return stream.getvalue()


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
            for item in assessment.control_results.filter(
                requirement__framework=assessment.framework
            ).select_related(
                "requirement", "primary_owner__user"
            ).prefetch_related("evidence_artifacts", "remediation_plans")
        }
        multi_sheet = workbook.create_sheet("Multi-Framework Results", 3)
        multi_headers = (
            "Framework Code", "Framework Name", "Version", "Primary",
            "Requirement ID", "Domain", "Title", "Statement", "Status",
            "Implementation State", "Calculated Deduction", "Control Owner",
            "SSP Reference", "Assessor Notes / Findings", "Evidence References",
        )
        for column, header in enumerate(multi_headers, 1):
            multi_sheet.cell(1, column, header)
        for offset, result in enumerate(
            assessment.control_results.select_related(
                "requirement__framework", "primary_owner__user"
            ).prefetch_related("evidence_artifacts"), 2
        ):
            framework = result.requirement.framework
            artifacts = list(result.evidence_artifacts.all())
            values = (
                framework.code, framework.name, framework.version,
                "Yes" if framework.pk == assessment.framework_id else "No",
                result.requirement.requirement_id, result.requirement.domain,
                result.requirement.title, result.requirement.statement, result.status,
                result.implementation_state,
                result.calculated_deduction if framework.scoring_method != "NONE" else "",
                _display_member(result.primary_owner) or result.control_owner,
                result.ssp_reference, result.assessor_notes_findings,
                "; ".join(f"EA-{item.id:04d} {item.title}" for item in artifacts),
            )
            for column, value in enumerate(values, 1):
                multi_sheet.cell(offset, column, value)
        multi_sheet.freeze_panes = "A2"
        multi_sheet.auto_filter.ref = multi_sheet.dimensions
        for column in range(1, len(multi_headers) + 1):
            multi_sheet.column_dimensions[chr(64 + column)].width = 20
        objective_sheet = workbook.create_sheet("Objective Results", 4)
        objective_headers = (
            "Framework", "Requirement ID", "Objective ID", "Objective Text",
            "Status", "Assessor Notes", "Assessed By", "Assessed At",
            "Evidence References", "Examine Objects", "Interview Objects", "Test Objects",
        )
        for column, header in enumerate(objective_headers, 1):
            objective_sheet.cell(1, column, header)
        objective_results = ObjectiveAssessment.objects.filter(
            control_result__assessment=assessment
        ).select_related(
            "objective__requirement__framework", "assessed_by"
        ).prefetch_related("evidence", "objective__requirement__assessment_procedures")
        for row, result in enumerate(objective_results, 2):
            procedures = list(result.objective.requirement.assessment_procedures.all())
            method_text = lambda method: "; ".join(
                item.assessment_object for item in procedures if item.method == method
            )
            values = (
                result.objective.requirement.framework.code,
                result.objective.requirement.requirement_id, result.objective.objective_id,
                result.objective.text, result.get_status_display(), result.assessor_notes,
                (result.assessed_by.get_full_name() or result.assessed_by.username)
                if result.assessed_by else "", result.assessed_at,
                "; ".join(f"EA-{item.id:04d} {item.title}" for item in result.evidence.all()),
                method_text("EXAMINE"), method_text("INTERVIEW"), method_text("TEST"),
            )
            for column, value in enumerate(values, 1):
                objective_sheet.cell(row, column, value)
        objective_sheet.freeze_panes = "A2"
        objective_sheet.auto_filter.ref = objective_sheet.dimensions
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
