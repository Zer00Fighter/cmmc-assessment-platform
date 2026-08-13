from django.urls import path

from . import views

urlpatterns = [
    path("", views.organization_list, name="organization-list"),
    path("organizations/new/", views.organization_create, name="organization-create"),
    path("organizations/<slug:org_slug>/edit/", views.organization_edit, name="organization-edit"),
    path("organizations/<slug:org_slug>/members/", views.membership_list, name="membership-list"),
    path(
        "organizations/<slug:org_slug>/systems/", views.system_list, name="system-list"
    ),
    path("organizations/<slug:org_slug>/systems/new/", views.system_create, name="system-create"),
    path("organizations/<slug:org_slug>/systems/<int:system_id>/edit/", views.system_edit, name="system-edit"),
    path(
        "organizations/<slug:org_slug>/systems/<int:system_id>/assessments/",
        views.assessment_list,
        name="assessment-list",
    ),
    path(
        "organizations/<slug:org_slug>/systems/<int:system_id>/assessments/new/",
        views.assessment_create,
        name="assessment-create",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/",
        views.assessment_dashboard,
        name="assessment-dashboard",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/controls/<int:result_id>/",
        views.control_edit,
        name="control-edit",
    ),
    path(
        "organizations/<slug:org_slug>/assessments/<int:assessment_id>/owners/",
        views.bulk_control_owners, name="bulk-control-owners",
    ),
]
