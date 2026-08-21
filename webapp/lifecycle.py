from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import PurePosixPath
from uuid import UUID

from django.db import models

from .models import Organization


def _json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    return value


def _organization_graph(organization: Organization) -> dict[type[models.Model], set]:
    selected: dict[type[models.Model], set] = {Organization: {organization.pk}}
    webapp_models = list(Organization._meta.apps.get_app_config("webapp").get_models())
    changed = True
    while changed:
        changed = False
        for model in webapp_models:
            ids = selected.setdefault(model, set())
            query = models.Q()
            has_scope_relation = False
            for field in model._meta.fields:
                related = getattr(field, "related_model", None)
                if related in selected and selected[related]:
                    query |= models.Q(**{f"{field.name}__in": selected[related]})
                    has_scope_relation = True
            if not has_scope_relation:
                continue
            found = set(model._default_manager.filter(query).values_list("pk", flat=True))
            if not found.issubset(ids):
                ids.update(found)
                changed = True
    return {model: ids for model, ids in selected.items() if ids}


def _serialize_object(item: models.Model) -> dict:
    fields = {}
    for field in item._meta.fields:
        value = getattr(item, field.attname)
        if isinstance(field, models.FileField):
            value = value.name if value else ""
        fields[field.name] = _json_value(value)
    for field in item._meta.many_to_many:
        fields[field.name] = list(
            getattr(item, field.name).order_by("pk").values_list("pk", flat=True)
        )
    return {"pk": item.pk, "fields": fields}


def build_organization_export(organization: Organization) -> bytes:
    graph = _organization_graph(organization)
    snapshot = {
        "schema_version": 1,
        "export_type": "Omni organization data export",
        "organization": {"id": organization.pk, "slug": organization.slug, "name": organization.name},
        "authorized_users": [
            {
                "id": membership.user_id,
                "username": membership.user.username,
                "email": membership.user.email,
                "first_name": membership.user.first_name,
                "last_name": membership.user.last_name,
                "role": membership.role,
                "membership_active": membership.active,
            }
            for membership in organization.memberships.select_related("user").order_by("user_id")
        ],
        "models": {},
    }
    files = []
    for model in sorted(graph, key=lambda value: value._meta.label_lower):
        objects = list(model._default_manager.filter(pk__in=graph[model]).order_by("pk"))
        snapshot["models"][model._meta.label_lower] = [_serialize_object(item) for item in objects]
        for item in objects:
            for field in item._meta.fields:
                if not isinstance(field, models.FileField):
                    continue
                value = getattr(item, field.name)
                if value and value.name:
                    member = PurePosixPath("Files") / model._meta.model_name / str(item.pk) / PurePosixPath(value.name).name
                    files.append((member.as_posix(), value.storage, value.name))
    output = BytesIO()
    manifest_files = []
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as package:
        payload = json.dumps(snapshot, indent=2, ensure_ascii=False).encode("utf-8")
        package.writestr("Organization-Snapshot.json", payload)
        manifest_files.append({
            "path": "Organization-Snapshot.json", "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
        for member, storage, name in sorted(files, key=lambda value: value[0]):
            with storage.open(name, "rb") as source:
                payload = source.read()
            package.writestr(member, payload)
            manifest_files.append({
                "path": member, "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            })
        manifest = {
            "schema_version": 1,
            "export_type": "Omni organization data export",
            "organization_slug": organization.slug,
            "files": manifest_files,
        }
        package.writestr("Export-Manifest.json", json.dumps(manifest, indent=2))
    return output.getvalue()
