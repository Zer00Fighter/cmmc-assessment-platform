import tempfile
from datetime import date, timedelta
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from openpyxl import load_workbook

from .models import (
    Assessment,
    AuditEvent,
    ControlAssessment,
    EvidenceArtifact,
    EvidenceRequest,
    Framework,
    Membership,
    Organization,
    RemediationMilestone,
    RemediationPlan,
    Requirement,
    System,
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
            code="CMMC-L2", name="CMMC Level 2", version="2.13"
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
            {"framework": self.framework.id, "name": "New Assessment"},
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
