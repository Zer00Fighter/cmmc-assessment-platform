import tempfile
import hashlib
import zipfile
import sqlite3
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from .models import (
    Assessment,
    AssessmentAccess,
    AssessmentFramework,
    AssessmentObjective,
    AssessmentProcedure,
    AssessmentSample,
    AssessmentTeamMember,
    AuditEvent,
    ControlAssessment,
    EvidenceArtifact,
    EvidenceRequest,
    Framework,
    GeneratedDocument,
    Membership,
    LoginAttempt,
    Notification,
    NotificationPolicy,
    NotificationPreference,
    ObjectiveAssessment,
    Organization,
    OrganizationInvitation,
    RemediationMilestone,
    RemediationPlan,
    Requirement,
    RequirementMapping,
    System,
    WorkflowHistory,
    UserProfile,
)


class SprintOneWorkflowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.assessor = user_model.objects.create_user(
            "assessor", password="test-password"
        )
        self.outsider = user_model.objects.create_user(
            "outsider", password="test-password"
        )
        self.client_org = Organization.objects.create(name="Acme Defense", slug="acme")
        self.other_org = Organization.objects.create(name="Other Client", slug="other")
        Membership.objects.create(
            user=self.assessor,
            organization=self.client_org,
            role=Membership.Role.ASSESSOR,
        )
        Membership.objects.create(
            user=self.outsider,
            organization=self.other_org,
            role=Membership.Role.ASSESSOR,
        )
        self.system = System.objects.create(
            organization=self.client_org, name="CUI Enclave"
        )
        self.framework = Framework.objects.create(
            code="CMMC-L2", name="CMMC Level 2", version="2.13",
            scoring_method=Framework.ScoringMethod.SPRS, maximum_score=110,
        )
        self.requirement = Requirement.objects.create(
            framework=self.framework,
            requirement_id="AC.L2-3.1.1",
            domain="AC",
            title="Authorized Access Control",
            statement="Limit access to authorized users.",
            full_deduction=5,
        )
        self.assessment = Assessment.objects.create(
            system=self.system,
            framework=self.framework,
            name="2026 CMMC Assessment",
            created_by=self.assessor,
            status=Assessment.Status.IN_PROGRESS,
        )
        self.result = ControlAssessment.objects.create(
            assessment=self.assessment, requirement=self.requirement
        )

    def test_login_is_required(self):
        response = self.client.get(reverse("organization-list"))
        self.assertRedirects(response, f"{reverse('login')}?next=/")

    def test_tenant_membership_limits_organization_access(self):
        self.client.login(username="assessor", password="test-password")
        response = self.client.get(reverse("organization-list"))
        self.assertContains(response, "Acme Defense")
        self.assertNotContains(response, "Other Client")
        response = self.client.get(reverse("system-list", args=("other",)))
        self.assertEqual(response.status_code, 404)

    def test_create_assessment_loads_framework_controls(self):
        self.client.login(username="assessor", password="test-password")
        response = self.client.post(
            reverse("assessment-create", args=("acme", self.system.id)),
            {
                "frameworks": [self.framework.id],
                "primary_framework": self.framework.id,
                "name": "New Assessment",
            },
        )
        created = Assessment.objects.get(name="New Assessment")
        self.assertRedirects(
            response, reverse("assessment-dashboard", args=("acme", created.id))
        )
        self.assertEqual(created.control_results.count(), 1)

    def test_score_control_updates_dashboard_and_audit_log(self):
        self.client.login(username="assessor", password="test-password")
        response = self.client.post(
            reverse("control-edit", args=("acme", self.assessment.id, self.result.id)),
            {
                "status": ControlAssessment.Status.NOT_MET,
                "implementation_state": ControlAssessment.Implementation.NONE,
                "assessor_notes_findings": "Authorized-user evidence was incomplete.",
                "control_owner": "Security Officer",
                "ssp_reference": "SSP 3.1.1",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.result.refresh_from_db()
        self.assertEqual(self.result.calculated_deduction, 5)
        self.assertContains(response, "105")
        self.assertContains(response, "Authorized Access Control")
        self.assertTrue(
            AuditEvent.objects.filter(action="control_assessment.updated").exists()
        )

    def test_read_only_member_cannot_edit(self):
        viewer = get_user_model().objects.create_user(
            "viewer", password="test-password"
        )
        Membership.objects.create(
            user=viewer, organization=self.client_org, role=Membership.Role.VIEWER
        )
        self.client.login(username="viewer", password="test-password")
        response = self.client.get(
            reverse("control-edit", args=("acme", self.assessment.id, self.result.id))
        )
        self.assertEqual(response.status_code, 404)


class SprintTwoOnboardingTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_user(
            "orgadmin", email="admin@example.com", password="test-password"
        )
        self.owner_user = user_model.objects.create_user(
            "controlowner", email="owner@example.com", password="test-password"
        )
        self.client.login(username="orgadmin", password="test-password")

    def test_user_can_create_first_organization_and_becomes_admin(self):
        response = self.client.post(reverse("organization-create"), {
            "name": "Acme Defense", "legal_name": "Acme Defense LLC",
            "kind": Organization.Kind.CLIENT, "industry": "Defense",
            "primary_contact_email": "ciso@example.com",
        })
        organization = Organization.objects.get(name="Acme Defense")
        self.assertRedirects(response, reverse("system-list", args=(organization.slug,)))
        self.assertTrue(Membership.objects.filter(
            user=self.admin_user, organization=organization,
            role=Membership.Role.ADMIN,
        ).exists())

    def test_admin_can_onboard_system_and_existing_member(self):
        organization = Organization.objects.create(name="Acme", slug="acme")
        Membership.objects.create(
            user=self.admin_user, organization=organization, role=Membership.Role.ADMIN
        )
        response = self.client.post(reverse("system-create", args=("acme",)), {
            "name": "CUI Enclave", "description": "Protected environment",
            "system_owner_name": "Alex Owner", "system_owner_email": "alex@example.com",
            "environment": "Production", "data_types": "CUI", "scope": "In scope",
        })
        system = System.objects.get(name="CUI Enclave")
        self.assertRedirects(response, reverse("assessment-list", args=("acme", system.id)))
        response = self.client.post(reverse("membership-list", args=("acme",)), {
            "username_or_email": "owner@example.com", "role": Membership.Role.CLIENT,
        })
        self.assertRedirects(response, reverse("membership-list", args=("acme",)))
        self.assertTrue(Membership.objects.filter(
            user=self.owner_user, organization=organization,
            role=Membership.Role.CLIENT,
        ).exists())

    def test_bulk_owner_assignment_is_limited_to_organization_members(self):
        organization = Organization.objects.create(name="Acme", slug="acme")
        admin_membership = Membership.objects.create(
            user=self.admin_user, organization=organization, role=Membership.Role.ADMIN
        )
        owner_membership = Membership.objects.create(
            user=self.owner_user, organization=organization, role=Membership.Role.CLIENT
        )
        system = System.objects.create(organization=organization, name="Enclave")
        framework = Framework.objects.create(code="TEST", name="Test", version="1")
        requirement = Requirement.objects.create(
            framework=framework, requirement_id="AC.1", domain="AC",
            title="Access", statement="Control access.", full_deduction=1,
        )
        assessment = Assessment.objects.create(
            system=system, framework=framework, name="Assessment",
            created_by=self.admin_user,
        )
        result = ControlAssessment.objects.create(
            assessment=assessment, requirement=requirement
        )
        response = self.client.post(
            reverse("bulk-control-owners", args=("acme", assessment.id)),
            {"domain": "AC", "primary_owner": owner_membership.id,
             "supporting_owners": [admin_membership.id]},
        )
        self.assertRedirects(
            response, reverse("assessment-dashboard", args=("acme", assessment.id))
        )
        result.refresh_from_db()
        self.assertEqual(result.primary_owner, owner_membership)
        self.assertEqual(list(result.supporting_owners.all()), [admin_membership])


class SprintThreeEvidenceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.assessor = user_model.objects.create_user(
            "evidence-assessor", password="test-password"
        )
        self.client_user = user_model.objects.create_user(
            "evidence-client", password="test-password"
        )
        self.outsider = user_model.objects.create_user(
            "evidence-outsider", password="test-password"
        )
        self.organization = Organization.objects.create(name="Acme", slug="acme")
        self.other_org = Organization.objects.create(name="Other", slug="other-evidence")
        self.assessor_membership = Membership.objects.create(
            user=self.assessor, organization=self.organization,
            role=Membership.Role.ASSESSOR,
        )
        self.client_membership = Membership.objects.create(
            user=self.client_user, organization=self.organization,
            role=Membership.Role.CLIENT,
        )
        Membership.objects.create(
            user=self.outsider, organization=self.other_org,
            role=Membership.Role.ASSESSOR,
        )
        self.system = System.objects.create(
            organization=self.organization, name="CUI Enclave"
        )
        self.framework = Framework.objects.create(
            code="EVIDENCE-TEST", name="Evidence Test", version="1"
        )
        self.requirement = Requirement.objects.create(
            framework=self.framework, requirement_id="AC.1", domain="AC",
            title="Access Control", statement="Control access.", full_deduction=1,
        )
        self.assessment = Assessment.objects.create(
            system=self.system, framework=self.framework, name="Evidence Assessment",
            created_by=self.assessor, status=Assessment.Status.IN_PROGRESS,
        )
        self.control = ControlAssessment.objects.create(
            assessment=self.assessment, requirement=self.requirement
        )

    def test_curated_request_populates_canonical_object_and_control_mapping(self):
        self.client.login(username="evidence-assessor", password="test-password")
        response = self.client.post(
            reverse("evidence-request-create", args=("acme", self.assessment.id)),
            {
                "catalog_object": "EV-0001", "title": "", "description": "",
                "status": EvidenceRequest.Status.REQUESTED,
                "owner": self.client_membership.id, "controls": [self.control.id],
            },
        )
        request_item = EvidenceRequest.objects.get(assessment=self.assessment)
        self.assertRedirects(
            response, reverse("evidence-list", args=("acme", self.assessment.id))
        )
        self.assertEqual(request_item.evidence_code, "EV-0001")
        self.assertEqual(request_item.title, "Security Plan")
        self.assertEqual(list(request_item.controls.all()), [self.control])

    def test_generate_request_list_imports_optimized_drl_idempotently(self):
        self.framework.code = "CMMC-TEST"
        self.framework.save(update_fields=("code",))
        generated = SimpleNamespace(
            requests=[SimpleNamespace(
                requested_item="Access Control Policy",
                description="Provide the current policy.",
                controls=[SimpleNamespace(control_id="AC.1")],
            )]
        )
        self.client.login(username="evidence-assessor", password="test-password")
        url = reverse("evidence-request-generate", args=("acme", self.assessment.id))
        with patch("webapp.views._generate_cmmc_drl", return_value=generated):
            self.client.post(url)
            self.client.post(url)
        self.assertEqual(
            EvidenceRequest.objects.filter(title="Access Control Policy").count(), 1
        )
        item = EvidenceRequest.objects.get(title="Access Control Policy")
        self.assertEqual(list(item.controls.all()), [self.control])

    def test_client_can_register_artifact_and_request_becomes_received(self):
        request_item = EvidenceRequest.objects.create(
            assessment=self.assessment, title="Security Plan",
            created_by=self.assessor, owner=self.client_membership,
        )
        self.client.login(username="evidence-client", password="test-password")
        response = self.client.post(
            reverse("evidence-artifact-create", args=("acme", self.assessment.id)),
            {
                "title": "Current SSP", "external_reference": "https://example.com/ssp",
                "source": "GRC repository", "review_status": "ACCEPTED",
                "requests": [request_item.id], "controls": [self.control.id],
            },
        )
        self.assertRedirects(
            response, reverse("evidence-list", args=("acme", self.assessment.id))
        )
        artifact = EvidenceArtifact.objects.get(title="Current SSP")
        self.assertEqual(artifact.review_status, EvidenceArtifact.ReviewStatus.RECEIVED)
        request_item.refresh_from_db()
        self.assertEqual(request_item.status, EvidenceRequest.Status.RECEIVED)

    def test_assessor_acceptance_updates_request_and_dashboard_readiness(self):
        request_item = EvidenceRequest.objects.create(
            assessment=self.assessment, title="Security Plan", created_by=self.assessor
        )
        artifact = EvidenceArtifact.objects.create(
            organization=self.organization, assessment=self.assessment,
            title="SSP", external_reference="https://example.com/ssp",
            uploaded_by=self.client_user,
        )
        artifact.requests.add(request_item)
        self.client.login(username="evidence-assessor", password="test-password")
        response = self.client.post(
            reverse("evidence-artifact-edit", args=(
                "acme", self.assessment.id, artifact.id,
            )),
            {
                "title": "SSP", "external_reference": "https://example.com/ssp",
                "review_status": EvidenceArtifact.ReviewStatus.ACCEPTED,
                "assessor_notes": "Accepted and current.",
                "requests": [request_item.id], "controls": [self.control.id],
            },
        )
        self.assertRedirects(
            response, reverse("evidence-list", args=("acme", self.assessment.id))
        )
        request_item.refresh_from_db()
        self.assertEqual(request_item.status, EvidenceRequest.Status.ACCEPTED)
        dashboard = self.client.get(
            reverse("assessment-dashboard", args=("acme", self.assessment.id))
        )
        self.assertContains(dashboard, "100.0%")

    def test_cross_tenant_user_cannot_download_private_evidence(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                artifact = EvidenceArtifact.objects.create(
                    organization=self.organization, assessment=self.assessment,
                    title="Private Evidence",
                    file=SimpleUploadedFile("evidence.txt", b"private"),
                    uploaded_by=self.assessor,
                )
                self.client.login(username="evidence-outsider", password="test-password")
                response = self.client.get(
                    reverse("evidence-artifact-download", args=(
                        "acme", self.assessment.id, artifact.id,
                    ))
                )
                self.assertEqual(response.status_code, 404)


class SprintFourRemediationTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.admin = users.objects.create_user("rem-admin", password="test-password")
        self.assessor = users.objects.create_user("rem-assessor", password="test-password")
        self.owner = users.objects.create_user("rem-owner", password="test-password")
        self.outsider = users.objects.create_user("rem-outsider", password="test-password")
        self.organization = Organization.objects.create(name="Acme Remediation", slug="acme-rem")
        self.other_org = Organization.objects.create(name="Other Remediation", slug="other-rem")
        self.admin_member = Membership.objects.create(
            user=self.admin, organization=self.organization, role=Membership.Role.ADMIN
        )
        self.assessor_member = Membership.objects.create(
            user=self.assessor, organization=self.organization, role=Membership.Role.ASSESSOR
        )
        self.owner_member = Membership.objects.create(
            user=self.owner, organization=self.organization, role=Membership.Role.CLIENT
        )
        Membership.objects.create(
            user=self.outsider, organization=self.other_org, role=Membership.Role.ADMIN
        )
        self.system = System.objects.create(organization=self.organization, name="Enclave")
        self.framework = Framework.objects.create(code="REM", name="Remediation", version="1")
        self.requirement = Requirement.objects.create(
            framework=self.framework, requirement_id="AC.1", domain="AC",
            title="Access Control", statement="Control access.", full_deduction=5,
        )
        self.assessment = Assessment.objects.create(
            system=self.system, framework=self.framework, name="Remediation Assessment",
            created_by=self.assessor,
        )
        self.control = ControlAssessment.objects.create(
            assessment=self.assessment, requirement=self.requirement,
            status=ControlAssessment.Status.NOT_MET,
            assessor_notes_findings="Access reviews were not performed.",
        )

    def _plan(self, **overrides):
        values = {
            "assessment": self.assessment, "remediation_id": "RAP-0001",
            "title": "Restore access reviews",
            "weakness_description": "Access reviews were not performed.",
            "owner": self.owner_member, "date_identified": date.today(),
            "planned_completion": date.today() + timedelta(days=30),
            "created_by": self.assessor,
        }
        values.update(overrides)
        plan = RemediationPlan.objects.create(**values)
        plan.controls.add(self.control)
        return plan

    def _post_values(self, plan, **overrides):
        values = {
            "title": plan.title, "controls": [self.control.id],
            "weakness_description": plan.weakness_description,
            "root_cause": plan.root_cause, "corrective_action": plan.corrective_action,
            "compensating_controls": plan.compensating_controls,
            "closure_criteria": plan.closure_criteria, "owner": self.owner_member.id,
            "status": plan.status, "priority": plan.priority, "severity": plan.severity,
            "likelihood": plan.likelihood, "residual_risk": plan.residual_risk,
            "date_identified": plan.date_identified.isoformat(),
            "planned_completion": plan.planned_completion.isoformat(),
            "validation_status": plan.validation_status,
        }
        values.update(overrides)
        return values

    def test_create_from_finding_prefills_control_and_finding(self):
        self.client.login(username="rem-assessor", password="test-password")
        response = self.client.get(
            reverse("remediation-create", args=("acme-rem", self.assessment.id))
            + f"?control={self.control.id}"
        )
        self.assertContains(response, "Access reviews were not performed.")
        self.assertContains(response, "Remediate AC.1")

    def test_assigned_owner_can_update_but_cannot_self_validate(self):
        plan = self._plan(root_cause="Missing schedule", corrective_action="Perform reviews")
        self.client.login(username="rem-owner", password="test-password")
        response = self.client.post(
            reverse("remediation-edit", args=("acme-rem", self.assessment.id, plan.id)),
            self._post_values(plan, corrective_action="Perform quarterly reviews",
                              validation_status=RemediationPlan.ValidationStatus.VALIDATED),
        )
        self.assertRedirects(response, reverse(
            "remediation-detail", args=("acme-rem", self.assessment.id, plan.id)
        ))
        plan.refresh_from_db()
        self.assertEqual(plan.corrective_action, "Perform quarterly reviews")
        self.assertEqual(plan.validation_status, RemediationPlan.ValidationStatus.PENDING)

    def test_validated_plan_with_evidence_can_be_closed(self):
        plan = self._plan(
            root_cause="Missing schedule", corrective_action="Perform reviews",
            closure_criteria="Review approved and evidenced",
            status=RemediationPlan.Status.READY_VALIDATION,
        )
        artifact = EvidenceArtifact.objects.create(
            organization=self.organization, assessment=self.assessment,
            title="Completed review", external_reference="https://example.com/review",
            review_status=EvidenceArtifact.ReviewStatus.ACCEPTED, uploaded_by=self.owner,
        )
        self.client.login(username="rem-assessor", password="test-password")
        response = self.client.post(
            reverse("remediation-edit", args=("acme-rem", self.assessment.id, plan.id)),
            self._post_values(
                plan, status=RemediationPlan.Status.CLOSED,
                actual_completion=date.today().isoformat(),
                closure_evidence=[artifact.id],
                validation_status=RemediationPlan.ValidationStatus.VALIDATED,
                validation_notes="Closure verified.",
            ),
        )
        self.assertRedirects(response, reverse(
            "remediation-detail", args=("acme-rem", self.assessment.id, plan.id)
        ))
        plan.refresh_from_db()
        self.assertEqual(plan.status, RemediationPlan.Status.CLOSED)
        self.assertEqual(plan.validated_by, self.assessor)

    def test_cross_tenant_remediation_access_is_denied(self):
        plan = self._plan()
        self.client.login(username="rem-outsider", password="test-password")
        response = self.client.get(reverse(
            "remediation-detail", args=("acme-rem", self.assessment.id, plan.id)
        ))
        self.assertEqual(response.status_code, 404)

    def test_export_uses_workbook_poam_columns(self):
        self._plan(root_cause="Cause", corrective_action="Action")
        self.client.login(username="rem-assessor", password="test-password")
        response = self.client.get(reverse(
            "remediation-export", args=("acme-rem", self.assessment.id)
        ))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Disposition"],
            f'attachment; filename="Omni-{self.assessment.id}-Remediation-Action-Plan.xlsx"',
        )
        content = b"".join(response.streaming_content)
        sheet = load_workbook(BytesIO(content), read_only=True).active
        self.assertEqual(sheet.cell(5, 1).value, "Remediation ID (POA&M ID)")
        self.assertEqual(sheet.cell(5, 24).value, "Assessor Notes")
        self.assertEqual(sheet.cell(6, 2).value, "AC.1")


class SprintFiveReportingTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.assessor = users.objects.create_user("report-assessor", password="test-password")
        self.outsider = users.objects.create_user("report-outsider", password="test-password")
        self.organization = Organization.objects.create(name="Synthetic Defense", slug="synthetic")
        self.other_org = Organization.objects.create(name="Other Synthetic", slug="other-synthetic")
        Membership.objects.create(
            user=self.assessor, organization=self.organization, role=Membership.Role.ASSESSOR
        )
        Membership.objects.create(
            user=self.outsider, organization=self.other_org, role=Membership.Role.ASSESSOR
        )
        self.system = System.objects.create(
            organization=self.organization, name="Synthetic Enclave", scope="CUI enclave",
            cage_code="1AB23", system_owner_name="Synthetic Owner",
        )
        self.framework = Framework.objects.create(code="CMMC-REPORT", name="CMMC Level 2", version="2.13")
        self.requirement = Requirement.objects.create(
            framework=self.framework, requirement_id="AC.L2-3.1.1", domain="AC",
            title="Authorized Access Control", statement="Limit access.", full_deduction=5,
        )
        self.assessment = Assessment.objects.create(
            system=self.system, framework=self.framework, name="Synthetic Assessment",
            created_by=self.assessor, status=Assessment.Status.COMPLETE,
        )
        self.result = ControlAssessment.objects.create(
            assessment=self.assessment, requirement=self.requirement,
            status=ControlAssessment.Status.MET,
            implementation_state=ControlAssessment.Implementation.FULL,
            assessor_notes_findings="Access is restricted to authorized users.",
            ssp_reference="SSP 3.1.1",
        )

    def test_workbook_binds_web_assessment_data(self):
        from .reporting import build_assessment_workbook
        content = build_assessment_workbook(self.assessment)
        workbook = load_workbook(BytesIO(content), data_only=False, read_only=True)
        try:
            cover = workbook["Cover"]
            self.assertEqual(cover["C6"].value, "Synthetic Defense")
            assessment = workbook["Assessment"]
            self.assertEqual(assessment["I6"].value, "MET")
            self.assertEqual(assessment["R6"].value, "Access is restricted to authorized users.")
            crosswalk = workbook["SSP Crosswalk"]
            self.assertEqual(crosswalk["C6"].value, "SSP 3.1.1")
        finally:
            workbook.close()

    def test_package_embeds_upload_and_external_reference_text(self):
        from .reporting import build_package
        with tempfile.TemporaryDirectory() as directory:
            template = f"{directory}/private-template.docx"
            Path(template).touch()
            with override_settings(MEDIA_ROOT=directory, OMNI_SSP_TEMPLATE=template):
                artifact = EvidenceArtifact.objects.create(
                    organization=self.organization, assessment=self.assessment,
                    title="Access Review Evidence",
                    file=SimpleUploadedFile("access-review.txt", b"synthetic evidence"),
                    external_reference="https://example.com/access-review",
                    source="Synthetic repository",
                    review_status=EvidenceArtifact.ReviewStatus.ACCEPTED,
                    uploaded_by=self.assessor,
                )
                artifact.controls.add(self.result)
                with patch("webapp.reporting.build_word_ssp", return_value=b"synthetic docx"):
                    content, readiness = build_package(self.assessment, self.assessor)
            self.assertTrue(readiness["ready"])
            with zipfile.ZipFile(BytesIO(content)) as package:
                names = package.namelist()
                self.assertIn("Deliverables/Omni-Assessment-Workbook.xlsx", names)
                self.assertIn("Evidence/Evidence-Index.csv", names)
                upload = next(name for name in names if name.endswith("access-review.txt"))
                reference = next(name for name in names if name.endswith("External_Reference.txt"))
                self.assertEqual(package.read(upload), b"synthetic evidence")
                reference_text = package.read(reference).decode()
                self.assertIn("https://example.com/access-review", reference_text)
                self.assertIn("AC.L2-3.1.1", reference_text)

    def test_download_creates_metadata_history_without_persisting_client_file(self):
        self.client.login(username="report-assessor", password="test-password")
        with patch("webapp.reporting.build_assessment_workbook", return_value=b"workbook"):
            response = self.client.get(reverse(
                "report-download", args=("synthetic", self.assessment.id, "WORKBOOK")
            ))
        self.assertEqual(response.content, b"workbook")
        record = GeneratedDocument.objects.get(assessment=self.assessment)
        self.assertEqual(record.kind, GeneratedDocument.Kind.WORKBOOK)
        self.assertEqual(record.size_bytes, 8)
        self.assertFalse(hasattr(record, "file"))

    def test_cross_tenant_report_center_is_denied(self):
        self.client.login(username="report-outsider", password="test-password")
        response = self.client.get(reverse(
            "report-center", args=("synthetic", self.assessment.id)
        ))
        self.assertEqual(response.status_code, 404)


class SprintFivePointFiveFrameworkTests(TestCase):
    def setUp(self):
        user = get_user_model()
        self.assessor = user.objects.create_user("multi-assessor", password="test-password")
        self.organization = Organization.objects.create(name="Synthetic Multi", slug="multi")
        Membership.objects.create(
            user=self.assessor, organization=self.organization, role=Membership.Role.ASSESSOR
        )
        self.system = System.objects.create(organization=self.organization, name="Shared System")
        self.cmmc = Framework.objects.create(
            code="CMMC-MULTI", name="CMMC Level 2", version="2.13",
            authority="DoD", scoring_method=Framework.ScoringMethod.SPRS,
            maximum_score=110,
        )
        self.iso = Framework.objects.create(
            code="ISO-MULTI", name="ISO Synthetic", version="2026",
            authority="ISO", scoring_method=Framework.ScoringMethod.NONE,
        )
        self.cmmc_req = Requirement.objects.create(
            framework=self.cmmc, requirement_id="AC.1", domain="AC",
            title="CMMC Access", statement="Restrict access.", full_deduction=5,
        )
        self.iso_req = Requirement.objects.create(
            framework=self.iso, requirement_id="AC.1", domain="Access",
            title="ISO Access", statement="Manage access.", full_deduction=1,
        )
        self.client.login(username="multi-assessor", password="test-password")

    def test_create_selects_multiple_frameworks_and_loads_native_requirements(self):
        response = self.client.post(
            reverse("assessment-create", args=("multi", self.system.id)),
            {"name": "Integrated Assessment", "frameworks": [self.cmmc.id, self.iso.id],
             "primary_framework": self.cmmc.id},
        )
        assessment = Assessment.objects.get(name="Integrated Assessment")
        self.assertRedirects(response, reverse(
            "assessment-dashboard", args=("multi", assessment.id)
        ))
        self.assertEqual(assessment.framework, self.cmmc)
        self.assertEqual(set(assessment.frameworks.all()), {self.cmmc, self.iso})
        self.assertEqual(assessment.control_results.count(), 2)
        self.assertEqual(
            assessment.control_results.filter(requirement__requirement_id="AC.1").count(), 2
        )

    def test_framework_scores_are_independent_and_non_scored_framework_has_no_score(self):
        assessment = Assessment.objects.create(
            system=self.system, framework=self.cmmc, name="Scored Multi",
            created_by=self.assessor,
        )
        AssessmentFramework.objects.create(
            assessment=assessment, framework=self.cmmc, is_primary=True,
            added_by=self.assessor,
        )
        AssessmentFramework.objects.create(
            assessment=assessment, framework=self.iso, added_by=self.assessor,
        )
        ControlAssessment.objects.create(
            assessment=assessment, requirement=self.cmmc_req,
            status=ControlAssessment.Status.NOT_MET,
        )
        ControlAssessment.objects.create(
            assessment=assessment, requirement=self.iso_req,
            status=ControlAssessment.Status.MET,
        )
        response = self.client.get(reverse(
            "assessment-dashboard", args=("multi", assessment.id)
        ))
        self.assertContains(response, "105")
        self.assertContains(response, "ISO-MULTI")
        self.assertContains(response, "1/1 assessed")

    def test_framework_with_recorded_work_cannot_be_removed(self):
        assessment = Assessment.objects.create(
            system=self.system, framework=self.cmmc, name="Protected Multi",
            created_by=self.assessor,
        )
        AssessmentFramework.objects.create(
            assessment=assessment, framework=self.cmmc, is_primary=True,
            added_by=self.assessor,
        )
        AssessmentFramework.objects.create(
            assessment=assessment, framework=self.iso, added_by=self.assessor,
        )
        ControlAssessment.objects.create(assessment=assessment, requirement=self.cmmc_req)
        ControlAssessment.objects.create(
            assessment=assessment, requirement=self.iso_req,
            status=ControlAssessment.Status.MET,
            assessor_notes_findings="Control is conforming.",
        )
        response = self.client.post(
            reverse("assessment-frameworks", args=("multi", assessment.id)),
            {"name": assessment.name, "frameworks": [self.cmmc.id],
             "primary_framework": self.cmmc.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot be removed")
        self.assertTrue(assessment.frameworks.filter(pk=self.iso.id).exists())

    def test_framework_catalog_displays_metadata(self):
        response = self.client.get(reverse("framework-catalog"))
        self.assertContains(response, "ISO Synthetic")
        self.assertContains(response, "No numeric score")

    def test_crosswalk_preserves_traceability_and_artifact_reuse(self):
        assessment = Assessment.objects.create(
            system=self.system, framework=self.cmmc, name="Mapped Multi",
            created_by=self.assessor,
        )
        AssessmentFramework.objects.create(
            assessment=assessment, framework=self.cmmc, is_primary=True,
            added_by=self.assessor,
        )
        AssessmentFramework.objects.create(
            assessment=assessment, framework=self.iso, added_by=self.assessor,
        )
        cmmc_result = ControlAssessment.objects.create(
            assessment=assessment, requirement=self.cmmc_req
        )
        iso_result = ControlAssessment.objects.create(
            assessment=assessment, requirement=self.iso_req
        )
        RequirementMapping.objects.create(
            source=self.cmmc_req, target=self.iso_req,
            relationship=RequirementMapping.Relationship.EQUIVALENT,
            mapping_reference="Synthetic crosswalk",
        )
        artifact = EvidenceArtifact.objects.create(
            organization=self.organization, assessment=assessment,
            title="Shared access evidence", external_reference="https://example.com/shared",
            uploaded_by=self.assessor,
        )
        artifact.controls.add(cmmc_result, iso_result)
        self.assertEqual(artifact.controls.count(), 2)
        response = self.client.get(reverse(
            "control-edit", args=("multi", assessment.id, cmmc_result.id)
        ))
        self.assertContains(response, "ISO-MULTI · AC.1")
        self.assertContains(response, "Equivalent")


class SprintSixExecutionTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.assessor = users.objects.create_user("s6-assessor", password="test-password")
        self.admin = users.objects.create_user("s6-admin", password="test-password")
        self.organization = Organization.objects.create(name="Synthetic S6", slug="s6")
        self.assessor_member = Membership.objects.create(
            user=self.assessor, organization=self.organization, role=Membership.Role.ASSESSOR
        )
        self.admin_member = Membership.objects.create(
            user=self.admin, organization=self.organization, role=Membership.Role.ADMIN
        )
        self.system = System.objects.create(organization=self.organization, name="S6 System")
        self.framework = Framework.objects.create(
            code="S6-FW", name="Sprint Six", version="1",
            scoring_method=Framework.ScoringMethod.DEDUCTION, maximum_score=100,
        )
        self.requirement = Requirement.objects.create(
            framework=self.framework, requirement_id="S6.1", domain="S6",
            title="Objective control", statement="Meet every objective.", full_deduction=5,
        )
        self.objective_a = AssessmentObjective.objects.create(
            requirement=self.requirement, objective_id="a", text="First objective"
        )
        self.objective_b = AssessmentObjective.objects.create(
            requirement=self.requirement, objective_id="b", text="Second objective"
        )
        AssessmentProcedure.objects.create(
            requirement=self.requirement, method=AssessmentProcedure.Method.EXAMINE,
            sequence=1, assessment_object="Policy",
        )
        self.assessment = Assessment.objects.create(
            system=self.system, framework=self.framework, name="S6 Assessment",
            created_by=self.assessor,
        )
        AssessmentFramework.objects.create(
            assessment=self.assessment, framework=self.framework, is_primary=True,
            added_by=self.assessor,
        )
        self.control = ControlAssessment.objects.create(
            assessment=self.assessment, requirement=self.requirement
        )
        self.result_a = ObjectiveAssessment.objects.create(
            control_result=self.control, objective=self.objective_a
        )
        self.result_b = ObjectiveAssessment.objects.create(
            control_result=self.control, objective=self.objective_b
        )

    def test_planning_records_scope_team_and_sampling_methodology(self):
        self.client.login(username="s6-assessor", password="test-password")
        url = reverse("assessment-plan", args=("s6", self.assessment.id))
        response = self.client.post(url, {
            "action": "plan", "engagement_start": "2026-08-01",
            "engagement_end": "2026-08-31", "scope_boundaries": "Synthetic boundary",
            "assessment_locations": "Remote", "sampling_methodology": "Random sample",
        })
        self.assertRedirects(response, url)
        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.sampling_methodology, "Random sample")
        response = self.client.post(url, {
            "action": "team", "team-membership": self.assessor_member.id,
            "team-role": AssessmentTeamMember.Role.LEAD,
        })
        self.assertRedirects(response, url)
        self.assertTrue(self.assessment.team_members.filter(role="LEAD").exists())

    def test_objectives_derive_control_status(self):
        self.client.login(username="s6-assessor", password="test-password")
        url_a = reverse("objective-edit", args=("s6", self.assessment.id, self.result_a.id))
        self.client.post(url_a, {
            "status": ObjectiveAssessment.Status.MET,
            "assessor_notes": "First objective met.",
        })
        url_b = reverse("objective-edit", args=("s6", self.assessment.id, self.result_b.id))
        self.client.post(url_b, {
            "status": ObjectiveAssessment.Status.NOT_MET,
            "assessor_notes": "Second objective failed.",
        })
        self.control.refresh_from_db()
        self.assertEqual(self.control.status, ControlAssessment.Status.NOT_MET)
        self.assertEqual(self.control.calculated_deduction, 5)

    def test_sample_cannot_exceed_population(self):
        self.client.login(username="s6-assessor", password="test-password")
        response = self.client.post(reverse(
            "sample-create", args=("s6", self.assessment.id)
        ), {
            "name": "Invalid sample", "population_description": "Accounts",
            "population_size": 5, "sample_size": 6,
            "selection_method": "Random",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cannot exceed the population size")
        self.assertFalse(AssessmentSample.objects.exists())

    def test_signoff_requires_review_then_locks_and_admin_reopens_with_reason(self):
        ObjectiveAssessment.objects.filter(control_result=self.control).update(
            status=ObjectiveAssessment.Status.MET, assessor_notes="Met"
        )
        self.control.derive_from_objectives()
        self.assessment.quality_review_status = "APPROVED"
        self.assessment.save(update_fields=("quality_review_status",))
        self.client.login(username="s6-assessor", password="test-password")
        response = self.client.post(reverse(
            "assessment-signoff", args=("s6", self.assessment.id)
        ))
        self.assertRedirects(response, reverse(
            "quality-review", args=("s6", self.assessment.id)
        ))
        self.assessment.refresh_from_db()
        self.assertTrue(self.assessment.locked)
        edit = self.client.get(reverse(
            "objective-edit", args=("s6", self.assessment.id, self.result_a.id)
        ))
        self.assertEqual(edit.status_code, 404)
        self.client.login(username="s6-admin", password="test-password")
        reopen = self.client.post(reverse(
            "assessment-reopen", args=("s6", self.assessment.id)
        ), {"reason": "New evidence requires reassessment."})
        self.assertRedirects(reopen, reverse(
            "assessment-dashboard", args=("s6", self.assessment.id)
        ))
        self.assessment.refresh_from_db()
        self.assertFalse(self.assessment.locked)
        self.assertEqual(self.assessment.reopen_reason, "New evidence requires reassessment.")


class SprintSevenDashboardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user("executive", password="test-password")
        self.outsider = user_model.objects.create_user("outside-exec", password="test-password")
        self.organization = Organization.objects.create(name="Synthetic Analytics", slug="analytics")
        other = Organization.objects.create(name="Other Analytics", slug="other-analytics")
        self.member = Membership.objects.create(
            user=self.user, organization=self.organization, role=Membership.Role.ASSESSOR
        )
        Membership.objects.create(user=self.outsider, organization=other, role=Membership.Role.VIEWER)
        system = System.objects.create(organization=self.organization, name="Analytics System")
        self.framework = Framework.objects.create(
            code="AN-FW", name="Analytics Framework", version="1",
            scoring_method=Framework.ScoringMethod.DEDUCTION, maximum_score=100,
        )
        met_requirement = Requirement.objects.create(
            framework=self.framework, requirement_id="AC-1", domain="AC",
            title="Access", statement="Control access.", full_deduction=5,
        )
        gap_requirement = Requirement.objects.create(
            framework=self.framework, requirement_id="IR-1", domain="IR",
            title="Respond", statement="Respond to incidents.", full_deduction=10,
        )
        self.assessment = Assessment.objects.create(
            system=system, framework=self.framework, name="Executive Assessment",
            created_by=self.user, status=Assessment.Status.IN_PROGRESS,
            quality_review_status="IN_REVIEW",
        )
        AssessmentFramework.objects.create(
            assessment=self.assessment, framework=self.framework, is_primary=True,
            added_by=self.user,
        )
        met = ControlAssessment.objects.create(
            assessment=self.assessment, requirement=met_requirement,
            status=ControlAssessment.Status.MET,
            implementation_state=ControlAssessment.Implementation.FULL,
            primary_owner=self.member,
        )
        gap = ControlAssessment.objects.create(
            assessment=self.assessment, requirement=gap_requirement,
            status=ControlAssessment.Status.NOT_MET,
            implementation_state=ControlAssessment.Implementation.NONE,
            primary_owner=self.member,
        )
        objective = AssessmentObjective.objects.create(
            requirement=met_requirement, objective_id="a", text="Verify access"
        )
        ObjectiveAssessment.objects.create(
            control_result=met, objective=objective, status=ObjectiveAssessment.Status.MET,
            assessed_by=self.user,
        )
        EvidenceRequest.objects.create(
            assessment=self.assessment, title="Overdue evidence",
            due_date=date.today() - timedelta(days=1), created_by=self.user,
        )
        RemediationPlan.objects.create(
            assessment=self.assessment, remediation_id="RAP-001", title="Close incident gap",
            weakness_description="Synthetic finding", created_by=self.user,
            date_identified=date.today(), planned_completion=date.today() - timedelta(days=1),
            priority=RemediationPlan.Priority.HIGH,
        ).controls.add(gap)

    def test_dashboard_shows_executive_analytics_and_domain_filter(self):
        self.client.login(username="executive", password="test-password")
        response = self.client.get(reverse(
            "assessment-dashboard", args=("analytics", self.assessment.id)
        ))
        self.assertContains(response, "Executive assessment dashboard")
        self.assertContains(response, "Objective completion")
        self.assertContains(response, "1 overdue")
        self.assertContains(response, "Control-owner workload")
        filtered = self.client.get(reverse(
            "assessment-dashboard", args=("analytics", self.assessment.id)
        ), {"domain": "AC"})
        self.assertContains(filtered, "Access")
        self.assertNotContains(filtered, "Respond")

    def test_csv_snapshot_is_tenant_scoped_and_audited(self):
        url = reverse("dashboard-export", args=("analytics", self.assessment.id))
        self.client.login(username="outside-exec", password="test-password")
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.login(username="executive", password="test-password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        content = response.content.decode("utf-8")
        self.assertIn("Omni Executive Assessment Snapshot", content)
        self.assertIn("AN-FW,AC-1,AC,MET", content)
        self.assertTrue(AuditEvent.objects.filter(
            organization=self.organization, action="dashboard.exported"
        ).exists())


class SprintEightWorkflowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.assessor = user_model.objects.create_user(
            "workflow-assessor", email="assessor@example.test", password="test-password"
        )
        self.owner = user_model.objects.create_user(
            "workflow-owner", email="owner@example.test", password="test-password"
        )
        self.organization = Organization.objects.create(name="Workflow Test", slug="workflow")
        Membership.objects.create(
            user=self.assessor, organization=self.organization, role=Membership.Role.ASSESSOR
        )
        self.owner_member = Membership.objects.create(
            user=self.owner, organization=self.organization, role=Membership.Role.CLIENT
        )
        system = System.objects.create(organization=self.organization, name="Workflow System")
        framework = Framework.objects.create(code="WF", name="Workflow", version="1")
        requirement = Requirement.objects.create(
            framework=framework, requirement_id="WF-1", domain="WF",
            title="Workflow", statement="Operate workflow."
        )
        self.assessment = Assessment.objects.create(
            system=system, framework=framework, name="Workflow Assessment",
            created_by=self.assessor,
        )
        self.control = ControlAssessment.objects.create(
            assessment=self.assessment, requirement=requirement
        )

    @override_settings(
        OMNI_EMAIL_ENABLED=True,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="Omni by R!SC <omni@example.test>",
    )
    def test_assignment_creates_in_app_email_audit_and_workflow_history(self):
        NotificationPreference.objects.create(
            user=self.owner, delivery=NotificationPreference.Delivery.EMAIL
        )
        self.client.login(username="workflow-assessor", password="test-password")
        response = self.client.post(reverse(
            "evidence-request-create", args=("workflow", self.assessment.id)
        ), {
            "title": "Access policy", "description": "Provide the policy",
            "status": EvidenceRequest.Status.REQUESTED, "owner": self.owner_member.id,
            "due_date": date.today() + timedelta(days=7), "notify_owner": "on",
            "controls": [self.control.id],
        })
        self.assertRedirects(response, reverse(
            "evidence-list", args=("workflow", self.assessment.id)
        ))
        notice = Notification.objects.get(recipient=self.owner)
        self.assertEqual(notice.email_status, Notification.EmailStatus.SENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("Provide the policy", mail.outbox[0].body)
        self.assertTrue(WorkflowHistory.objects.filter(event="evidence_request.assigned").exists())

    def test_notification_center_marks_only_own_notification_read(self):
        item = Notification.objects.create(
            recipient=self.owner, organization=self.organization, assessment=self.assessment,
            category=Notification.Category.SYSTEM, title="Assigned", message="Open Omni"
        )
        self.client.login(username="workflow-assessor", password="test-password")
        response = self.client.post(reverse("notification-read", args=(item.id,)))
        self.assertEqual(response.status_code, 404)
        item.refresh_from_db()
        self.assertIsNone(item.read_at)
        self.client.login(username="workflow-owner", password="test-password")
        self.client.post(reverse("notification-read", args=(item.id,)))
        item.refresh_from_db()
        self.assertIsNotNone(item.read_at)

    def test_rejected_evidence_requires_review_comment(self):
        artifact = EvidenceArtifact.objects.create(
            organization=self.organization, assessment=self.assessment, title="Synthetic link",
            external_reference="https://example.test/evidence", uploaded_by=self.owner,
        )
        self.client.login(username="workflow-assessor", password="test-password")
        response = self.client.post(reverse(
            "evidence-artifact-edit", args=("workflow", self.assessment.id, artifact.id)
        ), {
            "title": artifact.title, "external_reference": artifact.external_reference,
            "review_status": EvidenceArtifact.ReviewStatus.REJECTED,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Explain why the evidence was rejected")

    def test_reminder_command_is_idempotent_per_day(self):
        EvidenceRequest.objects.create(
            assessment=self.assessment, title="Due request", owner=self.owner_member,
            due_date=date.today(), created_by=self.assessor,
        )
        call_command("send_workflow_reminders")
        call_command("send_workflow_reminders")
        self.assertEqual(Notification.objects.filter(
            recipient=self.owner, category=Notification.Category.DEADLINE
        ).count(), 1)


class SprintEightOneGovernanceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            "policy-admin", email="admin@example.test", password="test-password"
        )
        self.owner = user_model.objects.create_user(
            "policy-owner", email="owner@example.test", password="test-password"
        )
        self.lead = user_model.objects.create_user(
            "policy-lead", email="lead@example.test", password="test-password"
        )
        self.organization = Organization.objects.create(name="Policy Test", slug="policy")
        Membership.objects.create(
            user=self.admin, organization=self.organization, role=Membership.Role.ADMIN
        )
        self.owner_member = Membership.objects.create(
            user=self.owner, organization=self.organization, role=Membership.Role.CLIENT
        )
        lead_member = Membership.objects.create(
            user=self.lead, organization=self.organization, role=Membership.Role.ASSESSOR
        )
        system = System.objects.create(
            organization=self.organization, name="Policy System",
            system_owner_name="Client Owner", system_owner_email="client-owner@example.test",
        )
        framework = Framework.objects.create(code="POL", name="Policy", version="1")
        requirement = Requirement.objects.create(
            framework=framework, requirement_id="POL-1", domain="POL",
            title="Policy", statement="Apply policy."
        )
        self.assessment = Assessment.objects.create(
            system=system, framework=framework, name="Policy Assessment", created_by=self.admin
        )
        self.control = ControlAssessment.objects.create(
            assessment=self.assessment, requirement=requirement
        )
        AssessmentTeamMember.objects.create(
            assessment=self.assessment, membership=lead_member,
            role=AssessmentTeamMember.Role.LEAD,
        )

    def test_per_action_toggle_suppresses_assignment_notification(self):
        self.client.login(username="policy-admin", password="test-password")
        self.client.post(reverse(
            "evidence-request-create", args=("policy", self.assessment.id)
        ), {
            "title": "Silent request", "status": EvidenceRequest.Status.REQUESTED,
            "owner": self.owner_member.id, "due_date": date.today() + timedelta(days=7),
            "controls": [self.control.id],
        })
        self.assertFalse(Notification.objects.filter(recipient=self.owner).exists())

    @override_settings(
        OMNI_EMAIL_ENABLED=True,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="Omni <omni@example.test>",
    )
    def test_daily_digest_queues_then_sends(self):
        NotificationPreference.objects.create(
            user=self.owner, delivery=NotificationPreference.Delivery.DAILY
        )
        from .notifications import notify
        notify(
            recipients=[self.owner], organization=self.organization,
            assessment=self.assessment, category=Notification.Category.ASSIGNMENT,
            title="Digest assignment", message="Open Omni", actor=self.admin,
        )
        notice = Notification.objects.get(recipient=self.owner)
        self.assertEqual(notice.email_status, Notification.EmailStatus.QUEUED)
        call_command("send_notification_digests")
        notice.refresh_from_db()
        self.assertEqual(notice.email_status, Notification.EmailStatus.SENT)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(
        OMNI_EMAIL_ENABLED=True,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="Omni <omni@example.test>",
    )
    def test_overdue_escalates_to_owner_lead_and_system_owner(self):
        NotificationPolicy.objects.create(
            organization=self.organization,
            escalation_recipients=NotificationPolicy.Escalation.CLIENT,
        )
        EvidenceRequest.objects.create(
            assessment=self.assessment, title="Escalated request", owner=self.owner_member,
            due_date=date.today() - timedelta(days=1), created_by=self.admin,
        )
        call_command("send_workflow_reminders")
        recipients = set(Notification.objects.values_list("recipient__username", flat=True))
        self.assertEqual(recipients, {"policy-owner", "policy-lead"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["client-owner@example.test"])

    def test_org_admin_can_update_notification_policy(self):
        self.client.login(username="policy-admin", password="test-password")
        response = self.client.post(reverse("notification-policy", args=("policy",)), {
            "first_reminder_days": 10, "second_reminder_days": 5,
            "notify_on_due_date": "on", "overdue_escalation_days": 2,
            "repeat_overdue_days": 14,
            "escalation_recipients": NotificationPolicy.Escalation.CLIENT,
        })
        self.assertRedirects(response, reverse("notification-policy", args=("policy",)))
        policy = self.organization.notification_policy
        self.assertEqual(policy.repeat_overdue_days, 14)
        self.assertFalse(policy.notifications_enabled)


class SprintNineAccessGovernanceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            "access-admin", email="admin@example.test", password="test-password"
        )
        self.member_user = user_model.objects.create_user(
            "access-member", email="member@example.test", password="test-password"
        )
        self.other_user = user_model.objects.create_user(
            "access-other", email="other@example.test", password="test-password"
        )
        self.organization = Organization.objects.create(name="Access Test", slug="access")
        self.admin_member = Membership.objects.create(
            user=self.admin, organization=self.organization, role=Membership.Role.ADMIN
        )
        self.member = Membership.objects.create(
            user=self.member_user, organization=self.organization, role=Membership.Role.CLIENT
        )
        self.other_member = Membership.objects.create(
            user=self.other_user, organization=self.organization, role=Membership.Role.CLIENT
        )
        self.system = System.objects.create(organization=self.organization, name="Access System")
        framework = Framework.objects.create(code="ACCESS", name="Access", version="1")
        requirement = Requirement.objects.create(
            framework=framework, requirement_id="ACCESS-1", domain="AC",
            title="Access", statement="Restrict access."
        )
        self.assessment = Assessment.objects.create(
            system=self.system, framework=framework, name="Restricted Assessment",
            created_by=self.admin,
        )
        self.control = ControlAssessment.objects.create(
            assessment=self.assessment, requirement=requirement, primary_owner=self.member
        )

    @override_settings(
        OMNI_EMAIL_ENABLED=True,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="Omni <omni@example.test>",
    )
    @patch("webapp.views.secrets.token_urlsafe", return_value="fixed-secure-token")
    def test_invitation_email_acceptance_creates_account_and_membership(self, token_mock):
        self.client.login(username="access-admin", password="test-password")
        response = self.client.post(reverse("membership-list", args=("access",)), {
            "action": "invite", "email": "new-user@example.test",
            "role": Membership.Role.VIEWER,
        })
        self.assertRedirects(response, reverse("membership-list", args=("access",)))
        invitation = OrganizationInvitation.objects.get(email="new-user@example.test")
        self.assertNotIn("fixed-secure-token", invitation.token_digest)
        self.assertEqual(len(mail.outbox), 1)
        self.client.logout()
        accepted = self.client.post(reverse("invitation-accept", args=("fixed-secure-token",)), {
            "first_name": "New", "last_name": "User",
            "password1": "A-Strong-Test-Password-482!",
            "password2": "A-Strong-Test-Password-482!",
        })
        self.assertRedirects(accepted, reverse("organization-list"))
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, OrganizationInvitation.Status.ACCEPTED)
        self.assertTrue(Membership.objects.filter(
            user__email="new-user@example.test", organization=self.organization,
            role=Membership.Role.VIEWER, active=True,
        ).exists())

    def test_expired_invitation_is_rejected(self):
        invitation = OrganizationInvitation.objects.create(
            organization=self.organization, email="expired@example.test",
            role=Membership.Role.CLIENT, token_digest=hashlib.sha256(b"expired").hexdigest(),
            invited_by=self.admin, expires_at=timezone.now() - timedelta(minutes=1),
        )
        response = self.client.get(reverse("invitation-accept", args=("expired",)))
        self.assertEqual(response.status_code, 410)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, OrganizationInvitation.Status.PENDING)

    def test_explicit_assessment_access_restricts_other_members(self):
        AssessmentAccess.objects.create(
            assessment=self.assessment, membership=self.member,
            access=AssessmentAccess.Access.VIEW, granted_by=self.admin,
        )
        url = reverse("assessment-dashboard", args=("access", self.assessment.id))
        self.client.login(username="access-member", password="test-password")
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.login(username="access-other", password="test-password")
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.login(username="access-admin", password="test-password")
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_last_admin_cannot_be_deactivated(self):
        self.client.login(username="access-admin", password="test-password")
        response = self.client.post(reverse(
            "membership-toggle", args=("access", self.admin_member.id)
        ), {"confirm": "yes"})
        self.assertRedirects(response, reverse("membership-list", args=("access",)))
        self.admin_member.refresh_from_db()
        self.assertTrue(self.admin_member.active)

    def test_assignment_warning_precedes_deactivation(self):
        self.client.login(username="access-admin", password="test-password")
        url = reverse("membership-toggle", args=("access", self.member.id))
        self.client.post(url)
        self.member.refresh_from_db()
        self.assertTrue(self.member.active)
        self.client.post(url, {"confirm": "yes"})
        self.member.refresh_from_db()
        self.assertFalse(self.member.active)

    def test_profile_and_access_review_export(self):
        self.client.login(username="access-admin", password="test-password")
        profile = self.client.post(reverse("user-profile"), {
            "first_name": "Access", "last_name": "Admin", "email": "admin@example.test",
            "job_title": "GRC Administrator", "phone": "555-0100",
            "time_zone": "America/New_York",
        })
        self.assertRedirects(profile, reverse("user-profile"))
        self.assertEqual(UserProfile.objects.get(user=self.admin).job_title, "GRC Administrator")
        export = self.client.get(reverse("access-review-export", args=("access",)))
        self.assertEqual(export.status_code, 200)
        self.assertIn("access-member", export.content.decode())
        self.assertTrue(AuditEvent.objects.filter(action="access_review.exported").exists())


class SprintTenLocalSecurityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            "security-admin", email="security@example.test", password="test-password"
        )
        self.organization = Organization.objects.create(name="Security Test", slug="security")
        Membership.objects.create(
            user=self.admin, organization=self.organization, role=Membership.Role.ADMIN
        )

    @override_settings(OMNI_LOGIN_FAILURE_LIMIT=3, OMNI_LOGIN_LOCKOUT_MINUTES=15)
    def test_login_throttle_blocks_repeated_failures(self):
        url = reverse("login")
        for _ in range(3):
            self.client.post(url, {"username": "security-admin", "password": "wrong"})
        blocked = self.client.post(url, {
            "username": "security-admin", "password": "test-password"
        })
        self.assertEqual(blocked.status_code, 200)
        self.assertContains(blocked, "Too many unsuccessful attempts")
        attempt = LoginAttempt.objects.get(identifier="security-admin")
        self.assertIsNotNone(attempt.blocked_until)

    def test_security_headers_are_present(self):
        response = self.client.get(reverse("login"))
        self.assertIn("default-src 'self'", response["Content-Security-Policy"])
        self.assertEqual(response["Permissions-Policy"], "camera=(), microphone=(), geolocation=()")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_uses_generic_response_and_sends_secure_link(self):
        known = self.client.post(reverse("password_reset"), {"email": "security@example.test"})
        unknown = self.client.post(reverse("password_reset"), {"email": "unknown@example.test"})
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.url, unknown.url)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/reset/", mail.outbox[0].body)
        self.assertNotIn("test-password", mail.outbox[0].body)

    def test_backup_and_verification_commands(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = root / "source.sqlite3"
            connection = sqlite3.connect(database)
            connection.execute("CREATE TABLE sample (value TEXT)")
            connection.execute("INSERT INTO sample VALUES ('synthetic')")
            connection.commit()
            connection.close()
            media = root / "private"
            media.mkdir()
            (media / "evidence.txt").write_text("synthetic evidence", encoding="utf-8")
            backup = root / "backups"
            with patch.dict(settings.DATABASES["default"], {"NAME": str(database)}), patch.object(
                settings, "MEDIA_ROOT", media
            ), patch.object(settings, "OMNI_BACKUP_DIR", backup):
                call_command("backup_omni")
                archive = next(backup.glob("*.zip"))
                call_command("verify_omni_backup", str(archive))
                with zipfile.ZipFile(archive) as source:
                    self.assertIn("private_uploads/evidence.txt", source.namelist())

    def test_expired_invitations_and_admin_health(self):
        OrganizationInvitation.objects.create(
            organization=self.organization, email="expired@example.test",
            role=Membership.Role.VIEWER, token_digest="e" * 64, invited_by=self.admin,
            expires_at=timezone.now() - timedelta(days=1),
        )
        call_command("expire_invitations")
        self.assertEqual(
            OrganizationInvitation.objects.get().status,
            OrganizationInvitation.Status.EXPIRED,
        )
        self.client.login(username="security-admin", password="test-password")
        response = self.client.get(reverse("system-health", args=("security",)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Future deployment gate")
