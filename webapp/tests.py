from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    Assessment,
    AuditEvent,
    ControlAssessment,
    Framework,
    Membership,
    Organization,
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
