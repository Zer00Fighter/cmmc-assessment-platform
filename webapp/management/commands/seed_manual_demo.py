"""Seed an isolated, synthetic dataset used only for public manual screenshots."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from webapp.models import (
    Assessment,
    AssessmentFramework,
    AssessmentObjective,
    AssessmentTeamMember,
    ControlAssessment,
    EvidenceArtifact,
    EvidenceRequest,
    Framework,
    Membership,
    ObjectiveAssessment,
    Organization,
    RemediationPlan,
    Requirement,
    RiskRegisterEntry,
    System,
)


class Command(BaseCommand):
    help = "Create the synthetic, non-client dataset used for Omni manual screenshots."

    def handle(self, *args, **options):
        today = timezone.localdate()
        user_model = get_user_model()
        admin, _ = user_model.objects.update_or_create(
            username="manual-admin",
            defaults={
                "first_name": "Jordan",
                "last_name": "Assessor",
                "email": "jordan.assessor@example.test",
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin.set_password("OmniManualDemo!2026")
        admin.save(update_fields=["password"])

        framework, _ = Framework.objects.update_or_create(
            code="ESF-2026",
            defaults={
                "name": "Example Security Framework",
                "version": "2026.1",
                "authority": "Example Standards Council",
                "description": "Synthetic framework used only for public Omni documentation.",
                "scoring_method": Framework.ScoringMethod.NONE,
                "active": True,
            },
        )
        requirements_data = [
            ("AC-01", "Identity and Access Management", "Access Governance", "Access is authorized, reviewed, and removed based on business need."),
            ("AM-01", "Asset Management", "Asset Inventory", "Technology and information assets are inventoried and assigned accountable owners."),
            ("AU-01", "Security Operations", "Audit Logging", "Security-relevant events are logged, protected, reviewed, and retained."),
            ("BC-01", "Business Resilience", "Continuity Planning", "Critical services maintain tested continuity and recovery capabilities."),
            ("IR-01", "Incident Management", "Incident Response", "Security incidents are identified, contained, investigated, and resolved."),
            ("TP-01", "Third-Party Risk Management", "Supplier Assurance", "Third parties are evaluated and monitored according to risk."),
        ]
        requirements = []
        for index, (identifier, domain, title, statement) in enumerate(requirements_data, 1):
            requirement, _ = Requirement.objects.update_or_create(
                framework=framework,
                requirement_id=identifier,
                defaults={
                    "domain": domain,
                    "title": title,
                    "statement": statement,
                    "risk_weight": min(10, index + 3),
                },
            )
            requirements.append(requirement)
            for sequence, method in enumerate(("EXAMINE", "INTERVIEW", "TEST"), 1):
                AssessmentObjective.objects.update_or_create(
                    requirement=requirement,
                    objective_id=f"{identifier}.{sequence}",
                    defaults={
                        "text": f"Determine whether {statement[0].lower() + statement[1:]}",
                    },
                )

        organization, _ = Organization.objects.update_or_create(
            slug="example-organization",
            defaults={
                "name": "Example Organization",
                "industry": "Demonstration",
                "address": "100 Example Avenue\nSample City, ST 00000",
            },
        )
        membership, _ = Membership.objects.update_or_create(
            user=admin,
            organization=organization,
            defaults={"role": Membership.Role.ADMIN, "active": True},
        )
        system, _ = System.objects.update_or_create(
            organization=organization,
            name="Example Business System",
            defaults={
                "description": "Synthetic business system for Omni product documentation.",
                "system_owner_name": "Taylor System Owner",
                "system_owner_email": "taylor.owner@example.test",
                "location": "Sample City",
                "environment": "Hybrid demonstration environment",
                "data_types": "Synthetic business and operational data",
                "scope": "Example application, identity platform, endpoints, and supporting services.",
            },
        )
        assessment, _ = Assessment.objects.update_or_create(
            system=system,
            name="2026 Example Security Assessment",
            defaults={
                "framework": framework,
                "created_by": admin,
                "status": Assessment.Status.IN_PROGRESS,
                "engagement_start": today - timedelta(days=14),
                "engagement_end": today + timedelta(days=30),
                "assessment_locations": "Remote and Sample City office",
                "scope_boundaries": "Example Business System and supporting services",
                "sampling_methodology": "Risk-based representative sampling",
                "risk_management_enabled": True,
                "include_risk_in_reports": True,
            },
        )
        AssessmentFramework.objects.update_or_create(
            assessment=assessment,
            framework=framework,
            defaults={"is_primary": True, "added_by": admin},
        )
        AssessmentTeamMember.objects.update_or_create(
            assessment=assessment,
            membership=membership,
            defaults={"role": AssessmentTeamMember.Role.LEAD},
        )

        statuses = [
            (ControlAssessment.Status.MET, ControlAssessment.Implementation.FULL, "Access approvals and quarterly reviews were examined and found operating as designed."),
            (ControlAssessment.Status.MET, ControlAssessment.Implementation.FULL, "The asset inventories identify owners, status, and system relationships."),
            (ControlAssessment.Status.NOT_MET, ControlAssessment.Implementation.PARTIAL, "Finding: log review evidence was unavailable for two sampled weeks."),
            (ControlAssessment.Status.MET, ControlAssessment.Implementation.FULL, "Continuity plans and the latest exercise record support the requirement."),
            (ControlAssessment.Status.NOT_ASSESSED, ControlAssessment.Implementation.UNASSESSED, ""),
            (ControlAssessment.Status.NOT_ASSESSED, ControlAssessment.Implementation.UNASSESSED, ""),
        ]
        controls = []
        for requirement, (status, implementation, notes) in zip(requirements, statuses):
            control, _ = ControlAssessment.objects.update_or_create(
                assessment=assessment,
                requirement=requirement,
                defaults={
                    "status": status,
                    "implementation_state": implementation,
                    "assessor_notes_findings": notes,
                    "primary_owner": membership,
                    "updated_by": admin,
                },
            )
            controls.append(control)
            for objective in requirement.objectives.all():
                ObjectiveAssessment.objects.update_or_create(
                    control_result=control,
                    objective=objective,
                    defaults={
                        "status": "MET" if status == ControlAssessment.Status.MET else ("NOT_MET" if status == ControlAssessment.Status.NOT_MET else "NOT_ASSESSED"),
                        "assessor_notes": notes or "Assessment work is scheduled.",
                        "assessed_by": admin if status != ControlAssessment.Status.NOT_ASSESSED else None,
                    },
                )

        evidence_request, _ = EvidenceRequest.objects.update_or_create(
            assessment=assessment,
            title="Audit logging procedures and review records",
            defaults={
                "evidence_code": "EV-DEMO-01",
                "description": "Provide current logging procedures and recent review records.",
                "status": EvidenceRequest.Status.UNDER_REVIEW,
                "owner": membership,
                "due_date": today + timedelta(days=7),
                "created_by": admin,
                "notify_owner": False,
            },
        )
        evidence_request.controls.set([controls[2]])
        artifact, _ = EvidenceArtifact.objects.update_or_create(
            organization=organization,
            assessment=assessment,
            title="Example Audit Logging Procedure",
            defaults={
                "external_reference": "https://example.test/evidence/logging-procedure",
                "source": "Example Security Operations Team",
                "period_start": today - timedelta(days=90),
                "period_end": today,
                "expires_on": today + timedelta(days=275),
                "review_status": EvidenceArtifact.ReviewStatus.ACCEPTED,
                "assessor_notes": "Accepted for design; additional operating evidence requested.",
                "uploaded_by": admin,
            },
        )
        artifact.controls.set([controls[2]])
        artifact.requests.set([evidence_request])

        remediation, _ = RemediationPlan.objects.update_or_create(
            assessment=assessment,
            remediation_id="RAP-0001",
            defaults={
                "title": "Restore documented weekly log review",
                "weakness_description": "Two sampled weekly log reviews were not documented.",
                "root_cause": "Review ownership changed without a transition checklist.",
                "corrective_action": "Assign the review owner, automate reminders, and retain review records.",
                "closure_criteria": "Four consecutive weekly reviews are completed and independently validated.",
                "owner": membership,
                "status": RemediationPlan.Status.IN_PROGRESS,
                "priority": RemediationPlan.Priority.HIGH,
                "severity": RemediationPlan.Priority.HIGH,
                "date_identified": today - timedelta(days=3),
                "planned_completion": today + timedelta(days=30),
                "created_by": admin,
                "notify_owner": False,
            },
        )
        remediation.controls.set([controls[2]])

        risk, _ = RiskRegisterEntry.objects.update_or_create(
            organization=organization,
            risk_id="RISK-0001",
            defaults={
                "system": system,
                "assessment": assessment,
                "title": "Delayed detection of unauthorized activity",
                "description": "Incomplete log reviews may delay detection and response to unauthorized activity.",
                "category": "Security Operations",
                "source": "FINDING",
                "owner": membership,
                "status": RiskRegisterEntry.Status.TREATING,
                "likelihood": 3,
                "impact": 4,
                "inherent_score": 12,
                "treatment": RiskRegisterEntry.Treatment.MITIGATE,
                "treatment_plan": "Complete RAP-0001 and monitor weekly review evidence.",
                "target_date": today + timedelta(days=30),
                "residual_likelihood": 2,
                "residual_impact": 3,
                "residual_score": 6,
                "next_review_date": today + timedelta(days=30),
                "trend": "DECREASING",
                "monitoring_notes": "Treatment is progressing according to plan.",
                "created_by": admin,
            },
        )
        risk.controls.set([controls[2]])
        risk.remediation_plans.set([remediation])
        risk.supporting_evidence.set([artifact])

        self.stdout.write(self.style.SUCCESS(
            "Manual demo ready: manual-admin / Example Organization / assessment "
            f"{assessment.id}. This dataset is synthetic and contains no client data."
        ))
