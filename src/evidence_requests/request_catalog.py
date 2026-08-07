from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from src.evidence_requests.request_model import (
    ControlReference,
    EvidenceGuidance,
    EvidenceRequestCategory,
    EvidenceRequestPriority,
    EvidenceRequestType,
    ObjectiveReference,
)


class EvidenceRequestCatalogError(ValueError):
    """Raised when an evidence request catalog is invalid."""


class EvidenceRequestCatalogNotFoundError(
    EvidenceRequestCatalogError
):
    """Raised when a requested catalog entry cannot be found."""


@dataclass(frozen=True, slots=True)
class EvidenceRequestTemplate:
    """
    Framework-independent evidence request definition.

    This describes WHAT should be requested. It does not represent
    a live client request or contain request lifecycle state.
    """

    template_id: str
    framework_id: str
    title: str
    description: str

    category: EvidenceRequestCategory
    evidence_type: EvidenceRequestType

    primary_control: ControlReference

    related_controls: Sequence[ControlReference] = field(
        default_factory=tuple
    )

    objectives: Sequence[ObjectiveReference] = field(
        default_factory=tuple
    )

    guidance: Sequence[EvidenceGuidance] = field(
        default_factory=tuple
    )

    default_priority: EvidenceRequestPriority = (
        EvidenceRequestPriority.MEDIUM
    )

    suggested_owner: str = ""

    sprs_weight: Optional[int] = None

    reuse_key: str = ""

    tags: Sequence[str] = field(
        default_factory=tuple
    )

    source_reference: str = ""

    def __post_init__(self) -> None:
        template_id = self.template_id.strip()
        framework_id = self.framework_id.strip()
        title = self.title.strip()
        description = self.description.strip()
        suggested_owner = self.suggested_owner.strip()
        reuse_key = self.reuse_key.strip()
        source_reference = self.source_reference.strip()

        if not template_id:
            raise EvidenceRequestCatalogError(
                "template_id cannot be blank."
            )

        if not framework_id:
            raise EvidenceRequestCatalogError(
                "framework_id cannot be blank."
            )

        if not title:
            raise EvidenceRequestCatalogError(
                "title cannot be blank."
            )

        if not description:
            raise EvidenceRequestCatalogError(
                "description cannot be blank."
            )

        if (
            self.primary_control.framework_id.upper()
            != framework_id.upper()
        ):
            raise EvidenceRequestCatalogError(
                "primary_control.framework_id must match "
                "the template framework_id."
            )

        if (
            self.sprs_weight is not None
            and self.sprs_weight < 0
        ):
            raise EvidenceRequestCatalogError(
                "sprs_weight cannot be negative."
            )

        object.__setattr__(
            self,
            "template_id",
            template_id,
        )

        object.__setattr__(
            self,
            "framework_id",
            framework_id,
        )

        object.__setattr__(
            self,
            "title",
            title,
        )

        object.__setattr__(
            self,
            "description",
            description,
        )

        object.__setattr__(
            self,
            "suggested_owner",
            suggested_owner,
        )

        object.__setattr__(
            self,
            "reuse_key",
            reuse_key,
        )

        object.__setattr__(
            self,
            "source_reference",
            source_reference,
        )

        object.__setattr__(
            self,
            "related_controls",
            tuple(self.related_controls),
        )

        object.__setattr__(
            self,
            "objectives",
            tuple(self.objectives),
        )

        object.__setattr__(
            self,
            "guidance",
            tuple(self.guidance),
        )

        object.__setattr__(
            self,
            "tags",
            tuple(
                self._normalize_tags(
                    self.tags
                )
            ),
        )

    @property
    def all_controls(
        self,
    ) -> Sequence[ControlReference]:
        result: List[ControlReference] = []
        seen = set()

        for control in (
            self.primary_control,
            *self.related_controls,
        ):
            key = (
                control.framework_id.upper(),
                control.control_id.upper(),
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(control)

        return tuple(result)

    @property
    def control_ids(
        self,
    ) -> Sequence[str]:
        return tuple(
            control.control_id
            for control in self.all_controls
        )

    @staticmethod
    def _normalize_tags(
        tags: Iterable[str],
    ) -> List[str]:
        result: List[str] = []
        seen = set()

        for tag in tags:
            value = str(tag).strip()

            if not value:
                continue

            key = value.lower()

            if key in seen:
                continue

            seen.add(key)
            result.append(value)

        return result


class EvidenceRequestCatalog:
    """
    Framework-independent evidence knowledge catalog.

    Responsibilities:

    - load structured catalog content;
    - validate catalog entries;
    - locate templates by framework;
    - locate templates by control;
    - locate templates by objective;
    - search by tags and text;
    - identify reusable evidence templates.

    Framework-specific knowledge belongs in external content files,
    not in this class.
    """

    SUPPORTED_SCHEMA_VERSION = "1.0"

    def __init__(
        self,
        templates: Iterable[
            EvidenceRequestTemplate
        ] = (),
    ) -> None:
        self._templates: Dict[
            str,
            EvidenceRequestTemplate,
        ] = {}

        for template in templates:
            self.add(template)

    @property
    def count(self) -> int:
        return len(self._templates)

    def templates(
        self,
    ) -> List[EvidenceRequestTemplate]:
        return list(
            self._templates.values()
        )

    def add(
        self,
        template: EvidenceRequestTemplate,
    ) -> None:
        key = self._template_key(
            template.framework_id,
            template.template_id,
        )

        if key in self._templates:
            raise EvidenceRequestCatalogError(
                "Duplicate evidence request template: "
                f"{template.framework_id}/"
                f"{template.template_id}"
            )

        self._templates[key] = template

    def get(
        self,
        framework_id: str,
        template_id: str,
    ) -> EvidenceRequestTemplate:
        key = self._template_key(
            framework_id,
            template_id,
        )

        try:
            return self._templates[key]

        except KeyError as error:
            raise (
                EvidenceRequestCatalogNotFoundError(
                    "Evidence request template not found: "
                    f"{framework_id}/{template_id}"
                )
            ) from error

    def find(
        self,
        framework_id: str,
        template_id: str,
    ) -> Optional[EvidenceRequestTemplate]:
        return self._templates.get(
            self._template_key(
                framework_id,
                template_id,
            )
        )

    def for_framework(
        self,
        framework_id: str,
    ) -> List[EvidenceRequestTemplate]:
        framework_key = (
            self._normalize(framework_id)
        )

        return [
            template
            for template in self._templates.values()
            if self._normalize(
                template.framework_id
            )
            == framework_key
        ]

    def for_control(
        self,
        framework_id: str,
        control_id: str,
    ) -> List[EvidenceRequestTemplate]:
        framework_key = (
            self._normalize(framework_id)
        )

        control_key = self._normalize(
            control_id
        )

        matches: List[
            EvidenceRequestTemplate
        ] = []

        for template in self._templates.values():
            if (
                self._normalize(
                    template.framework_id
                )
                != framework_key
            ):
                continue

            if any(
                self._normalize(
                    control.control_id
                )
                == control_key
                for control
                in template.all_controls
            ):
                matches.append(template)

        return matches

    def for_objective(
        self,
        framework_id: str,
        control_id: str,
        objective_id: str,
    ) -> List[EvidenceRequestTemplate]:
        framework_key = (
            self._normalize(framework_id)
        )

        control_key = self._normalize(
            control_id
        )

        objective_key = self._normalize(
            objective_id
        )

        matches: List[
            EvidenceRequestTemplate
        ] = []

        for template in self._templates.values():
            if (
                self._normalize(
                    template.framework_id
                )
                != framework_key
            ):
                continue

            if any(
                self._normalize(
                    objective.control_id
                )
                == control_key
                and self._normalize(
                    objective.objective_id
                )
                == objective_key
                for objective
                in template.objectives
            ):
                matches.append(template)

        return matches

    def for_reuse_key(
        self,
        reuse_key: str,
    ) -> List[EvidenceRequestTemplate]:
        key = self._normalize(
            reuse_key
        )

        if not key:
            return []

        return [
            template
            for template in self._templates.values()
            if self._normalize(
                template.reuse_key
            )
            == key
        ]

    def for_tag(
        self,
        tag: str,
    ) -> List[EvidenceRequestTemplate]:
        tag_key = self._normalize(
            tag
        )

        return [
            template
            for template in self._templates.values()
            if any(
                self._normalize(item)
                == tag_key
                for item in template.tags
            )
        ]

    def search(
        self,
        text: str,
        *,
        framework_id: Optional[str] = None,
    ) -> List[EvidenceRequestTemplate]:
        query = self._normalize(
            text
        )

        if not query:
            return []

        framework_key = (
            self._normalize(framework_id)
            if framework_id
            else None
        )

        results: List[
            EvidenceRequestTemplate
        ] = []

        for template in self._templates.values():
            if (
                framework_key is not None
                and self._normalize(
                    template.framework_id
                )
                != framework_key
            ):
                continue

            haystack = " ".join(
                [
                    template.template_id,
                    template.title,
                    template.description,
                    template.suggested_owner,
                    template.reuse_key,
                    template.source_reference,
                    *template.tags,
                    *template.control_ids,
                    *[
                        guidance.description
                        for guidance
                        in template.guidance
                    ],
                    *[
                        example
                        for guidance
                        in template.guidance
                        for example
                        in guidance.example_artifacts
                    ],
                ]
            )

            if query in self._normalize(
                haystack
            ):
                results.append(template)

        return results

    @classmethod
    def from_file(
        cls,
        path: Path | str,
    ) -> "EvidenceRequestCatalog":
        path = Path(path)

        if not path.exists():
            raise EvidenceRequestCatalogError(
                f"Evidence catalog not found: {path}"
            )

        suffix = path.suffix.lower()

        if suffix == ".json":
            data = cls._load_json(
                path
            )

        elif suffix in {
            ".yaml",
            ".yml",
        }:
            data = cls._load_yaml(
                path
            )

        else:
            raise EvidenceRequestCatalogError(
                "Unsupported evidence catalog format: "
                f"{suffix}. Use .json, .yaml, or .yml."
            )

        return cls.from_mapping(
            data
        )

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[str, Any],
    ) -> "EvidenceRequestCatalog":
        if not isinstance(
            data,
            Mapping,
        ):
            raise EvidenceRequestCatalogError(
                "Evidence catalog root must "
                "be a mapping/object."
            )

        schema_version = str(
            data.get(
                "schema_version",
                "",
            )
        ).strip()

        if (
            schema_version
            != cls.SUPPORTED_SCHEMA_VERSION
        ):
            raise EvidenceRequestCatalogError(
                "Unsupported evidence catalog "
                f"schema_version: {schema_version!r}. "
                "Expected "
                f"{cls.SUPPORTED_SCHEMA_VERSION!r}."
            )

        framework_id = str(
            data.get(
                "framework_id",
                "",
            )
        ).strip()

        if not framework_id:
            raise EvidenceRequestCatalogError(
                "Catalog framework_id cannot be blank."
            )

        raw_templates = data.get(
            "templates"
        )

        if not isinstance(
            raw_templates,
            list,
        ):
            raise EvidenceRequestCatalogError(
                "Catalog templates must be a list."
            )

        catalog = cls()

        for index, raw_template in enumerate(
            raw_templates,
            start=1,
        ):
            try:
                template = (
                    cls._template_from_mapping(
                        framework_id,
                        raw_template,
                    )
                )

                catalog.add(
                    template
                )

            except (
                EvidenceRequestCatalogError,
                ValueError,
                TypeError,
                KeyError,
            ) as error:
                raise EvidenceRequestCatalogError(
                    "Invalid evidence catalog "
                    f"template #{index}: {error}"
                ) from error

        return catalog

    @classmethod
    def _template_from_mapping(
        cls,
        framework_id: str,
        data: Mapping[str, Any],
    ) -> EvidenceRequestTemplate:
        if not isinstance(
            data,
            Mapping,
        ):
            raise EvidenceRequestCatalogError(
                "Template must be an object."
            )

        primary_control_data = data.get(
            "primary_control"
        )

        if not isinstance(
            primary_control_data,
            Mapping,
        ):
            raise EvidenceRequestCatalogError(
                "primary_control must be an object."
            )

        primary_control = (
            cls._control_from_mapping(
                framework_id,
                primary_control_data,
            )
        )

        related_controls = tuple(
            cls._control_from_mapping(
                framework_id,
                item,
            )
            for item in cls._mapping_list(
                data.get(
                    "related_controls",
                    [],
                ),
                "related_controls",
            )
        )

        objectives = tuple(
            cls._objective_from_mapping(
                framework_id,
                item,
            )
            for item in cls._mapping_list(
                data.get(
                    "objectives",
                    [],
                ),
                "objectives",
            )
        )

        guidance = tuple(
            cls._guidance_from_mapping(
                item
            )
            for item in cls._mapping_list(
                data.get(
                    "guidance",
                    [],
                ),
                "guidance",
            )
        )

        try:
            category = (
                EvidenceRequestCategory(
                    str(
                        data["category"]
                    ).strip()
                )
            )

        except (
            KeyError,
            ValueError,
        ) as error:
            raise EvidenceRequestCatalogError(
                "Invalid or missing category."
            ) from error

        try:
            evidence_type = (
                EvidenceRequestType(
                    str(
                        data[
                            "evidence_type"
                        ]
                    ).strip()
                )
            )

        except (
            KeyError,
            ValueError,
        ) as error:
            raise EvidenceRequestCatalogError(
                "Invalid or missing evidence_type."
            ) from error

        priority_value = str(
            data.get(
                "default_priority",
                EvidenceRequestPriority
                .MEDIUM
                .value,
            )
        ).strip()

        try:
            priority = (
                EvidenceRequestPriority(
                    priority_value
                )
            )

        except ValueError as error:
            raise EvidenceRequestCatalogError(
                "Invalid default_priority: "
                f"{priority_value}"
            ) from error

        sprs_weight_value = data.get(
            "sprs_weight"
        )

        sprs_weight = (
            None
            if sprs_weight_value
            in {
                None,
                "",
            }
            else int(
                sprs_weight_value
            )
        )

        tags_raw = data.get(
            "tags",
            [],
        )

        if not isinstance(
            tags_raw,
            list,
        ):
            raise EvidenceRequestCatalogError(
                "tags must be a list."
            )

        return EvidenceRequestTemplate(
            template_id=str(
                data.get(
                    "template_id",
                    "",
                )
            ),
            framework_id=framework_id,
            title=str(
                data.get(
                    "title",
                    "",
                )
            ),
            description=str(
                data.get(
                    "description",
                    "",
                )
            ),
            category=category,
            evidence_type=evidence_type,
            primary_control=primary_control,
            related_controls=related_controls,
            objectives=objectives,
            guidance=guidance,
            default_priority=priority,
            suggested_owner=str(
                data.get(
                    "suggested_owner",
                    "",
                )
            ),
            sprs_weight=sprs_weight,
            reuse_key=str(
                data.get(
                    "reuse_key",
                    "",
                )
            ),
            tags=tuple(
                str(tag)
                for tag in tags_raw
            ),
            source_reference=str(
                data.get(
                    "source_reference",
                    "",
                )
            ),
        )

    @staticmethod
    def _control_from_mapping(
        framework_id: str,
        data: Mapping[str, Any],
    ) -> ControlReference:
        if not isinstance(
            data,
            Mapping,
        ):
            raise EvidenceRequestCatalogError(
                "Control reference must be an object."
            )

        return ControlReference(
            framework_id=framework_id,
            control_id=str(
                data.get(
                    "control_id",
                    "",
                )
            ),
            control_title=str(
                data.get(
                    "control_title",
                    "",
                )
            ),
        )

    @staticmethod
    def _objective_from_mapping(
        framework_id: str,
        data: Mapping[str, Any],
    ) -> ObjectiveReference:
        if not isinstance(
            data,
            Mapping,
        ):
            raise EvidenceRequestCatalogError(
                "Objective reference must be an object."
            )

        return ObjectiveReference(
            framework_id=framework_id,
            control_id=str(
                data.get(
                    "control_id",
                    "",
                )
            ),
            objective_id=str(
                data.get(
                    "objective_id",
                    "",
                )
            ),
            objective_text=str(
                data.get(
                    "objective_text",
                    "",
                )
            ),
        )

    @staticmethod
    def _guidance_from_mapping(
        data: Mapping[str, Any],
    ) -> EvidenceGuidance:
        if not isinstance(
            data,
            Mapping,
        ):
            raise EvidenceRequestCatalogError(
                "Evidence guidance must be an object."
            )

        try:
            evidence_type = (
                EvidenceRequestType(
                    str(
                        data[
                            "evidence_type"
                        ]
                    ).strip()
                )
            )

        except (
            KeyError,
            ValueError,
        ) as error:
            raise EvidenceRequestCatalogError(
                "Invalid guidance evidence_type."
            ) from error

        examples = data.get(
            "example_artifacts",
            [],
        )

        if not isinstance(
            examples,
            list,
        ):
            raise EvidenceRequestCatalogError(
                "example_artifacts must be a list."
            )

        return EvidenceGuidance(
            evidence_type=evidence_type,
            description=str(
                data.get(
                    "description",
                    "",
                )
            ),
            example_artifacts=tuple(
                str(item)
                for item in examples
            ),
            required=bool(
                data.get(
                    "required",
                    True,
                )
            ),
        )

    @staticmethod
    def _mapping_list(
        value: Any,
        field_name: str,
    ) -> List[Mapping[str, Any]]:
        if not isinstance(
            value,
            list,
        ):
            raise EvidenceRequestCatalogError(
                f"{field_name} must be a list."
            )

        result: List[
            Mapping[str, Any]
        ] = []

        for item in value:
            if not isinstance(
                item,
                Mapping,
            ):
                raise EvidenceRequestCatalogError(
                    f"{field_name} entries "
                    "must be objects."
                )

            result.append(item)

        return result

    @staticmethod
    def _load_json(
        path: Path,
    ) -> Mapping[str, Any]:
        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

        except (
            OSError,
            json.JSONDecodeError,
        ) as error:
            raise EvidenceRequestCatalogError(
                "Unable to load JSON evidence "
                f"catalog {path}: {error}"
            ) from error

        if not isinstance(
            data,
            Mapping,
        ):
            raise EvidenceRequestCatalogError(
                "JSON catalog root must "
                "be an object."
            )

        return data

    @staticmethod
    def _load_yaml(
        path: Path,
    ) -> Mapping[str, Any]:
        try:
            import yaml

        except ImportError as error:
            raise EvidenceRequestCatalogError(
                "YAML catalog support requires "
                "PyYAML. Install it with: "
                "pip install PyYAML"
            ) from error

        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = yaml.safe_load(
                    file
                )

        except (
            OSError,
            yaml.YAMLError,
        ) as error:
            raise EvidenceRequestCatalogError(
                "Unable to load YAML evidence "
                f"catalog {path}: {error}"
            ) from error

        if not isinstance(
            data,
            Mapping,
        ):
            raise EvidenceRequestCatalogError(
                "YAML catalog root must "
                "be an object."
            )

        return data

    @staticmethod
    def _template_key(
        framework_id: str,
        template_id: str,
    ) -> str:
        framework = (
            framework_id
            .strip()
            .upper()
        )

        template = (
            template_id
            .strip()
            .upper()
        )

        if not framework:
            raise EvidenceRequestCatalogError(
                "framework_id cannot be blank."
            )

        if not template:
            raise EvidenceRequestCatalogError(
                "template_id cannot be blank."
            )

        return (
            f"{framework}::{template}"
        )

    @staticmethod
    def _normalize(
        value: object,
    ) -> str:
        return (
            str(value)
            .strip()
            .casefold()
        )