from django.urls import path

from . import views

urlpatterns = [
    path("", views.organization_list, name="organization-list"),
    path(
        "organizations/<slug:org_slug>/systems/", views.system_list, name="system-list"
    ),
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
]
