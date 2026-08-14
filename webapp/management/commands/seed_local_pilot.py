from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from webapp.models import (
    Assessment, AssessmentFramework, ControlAssessment, EvidenceRequest, Framework,
    Membership, ObjectiveAssessment, Organization, RemediationPlan, System,
)


class Command(BaseCommand):
    help = "Create an idempotent, clearly synthetic local Omni pilot. Never use real client data."

    def add_arguments(self, parser):
        parser.add_argument("--confirm-synthetic", action="store_true")
        parser.add_argument("--created-by", default="")

    def handle(self, *args, **options):
        if not options["confirm_synthetic"]:
            raise CommandError("Pass --confirm-synthetic to acknowledge this creates local runtime data.")
        users = get_user_model().objects.filter(is_active=True)
        creator = users.filter(username=options["created_by"]).first() if options["created_by"] else None
        creator = creator or users.filter(is_superuser=True).first() or users.first()
        if not creator:
            raise CommandError("Create an Omni administrator account before seeding the pilot.")
        framework = Framework.objects.filter(active=True).order_by("id").first()
        if not framework:
            raise CommandError("Seed at least one framework before creating the pilot.")
        organization, _ = Organization.objects.get_or_create(
            slug="omni-synthetic-pilot",
            defaults={"name": "Omni Synthetic Pilot — NOT CLIENT DATA", "industry": "Synthetic"},
        )
        Membership.objects.update_or_create(
            user=creator, organization=organization,
            defaults={"role": Membership.Role.ADMIN, "active": True},
        )
        system, _ = System.objects.get_or_create(
            organization=organization, name="Synthetic CUI Enclave",
            defaults={
                "description": "Synthetic system used only for Omni local acceptance testing.",
                "system_owner_name": "Synthetic System Owner",
                "system_owner_email": "system-owner@example.test",
                "environment": "Local pilot", "scope": "Synthetic data only",
            },
        )
        assessment, created = Assessment.objects.get_or_create(
            system=system, name="Omni RC1 Synthetic Acceptance Assessment",
            defaults={
                "framework": framework, "created_by": creator,
                "status": Assessment.Status.IN_PROGRESS,
                "engagement_start": timezone.localdate(),
            },
        )
        if created:
            AssessmentFramework.objects.create(
                assessment=assessment, framework=framework, is_primary=True, added_by=creator
            )
            ControlAssessment.objects.bulk_create([
                ControlAssessment(assessment=assessment, requirement=requirement)
                for requirement in framework.requirements.all()
            ])
            for control in assessment.control_results.select_related("requirement"):
                ObjectiveAssessment.objects.bulk_create([
                    ObjectiveAssessment(control_result=control, objective=objective)
                    for objective in control.requirement.objectives.all()
                ])
            evidence_request = EvidenceRequest.objects.create(
                assessment=assessment, title="Synthetic access-control evidence",
                description="Provide synthetic policy and access-review records.",
                due_date=timezone.localdate(), created_by=creator, notify_owner=False,
            )
            first_control = assessment.control_results.first()
            if first_control:
                evidence_request.controls.add(first_control)
                plan = RemediationPlan.objects.create(
                    assessment=assessment, remediation_id="RAP-0001",
                    title="Synthetic pilot remediation", weakness_description="Synthetic finding only.",
                    created_by=creator, date_identified=timezone.localdate(), notify_owner=False,
                )
                plan.controls.add(first_control)
        for control in assessment.control_results.select_related("requirement"):
            for objective in control.requirement.objectives.all():
                ObjectiveAssessment.objects.get_or_create(
                    control_result=control, objective=objective
                )
        self.stdout.write(self.style.SUCCESS(
            f"Synthetic pilot ready: {organization.slug} / assessment {assessment.id}."
        ))
