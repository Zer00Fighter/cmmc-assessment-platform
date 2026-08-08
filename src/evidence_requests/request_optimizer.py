from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from src.evidence_requests.drl_model import (
    DocumentationRequest,
    DocumentationRequestCollection,
    DocumentationRequestControl,
    DocumentationRequestPriority,
    DocumentationRequestStatus,
    DocumentationRequestType,
)


class RequestOptimizerError(ValueError):
    """Raised when a Documentation Request List cannot be optimized."""


@dataclass(frozen=True, slots=True)
class RequestMergeRule:
    """
    Explicit deterministic merge rule.

    Every title in source_titles is treated as an approved wording variant
    or member of one client-facing evidence package.
    """

    package_title: str

    source_titles: Tuple[str, ...]

    evidence_type: DocumentationRequestType

    description: str = ""

    def __post_init__(self) -> None:
        package_title = self.package_title.strip()

        if not package_title:
            raise RequestOptimizerError(
                "RequestMergeRule.package_title cannot be blank."
            )

        normalized_titles = tuple(
            title.strip()
            for title in self.source_titles
            if title.strip()
        )

        if len(normalized_titles) < 2:
            raise RequestOptimizerError(
                "RequestMergeRule.source_titles must contain "
                "at least two non-blank titles."
            )

        keys = {
            title.casefold()
            for title in normalized_titles
        }

        if len(keys) != len(normalized_titles):
            raise RequestOptimizerError(
                "RequestMergeRule.source_titles cannot contain "
                "duplicate titles."
            )

        object.__setattr__(
            self,
            "package_title",
            package_title,
        )

        object.__setattr__(
            self,
            "source_titles",
            normalized_titles,
        )

        object.__setattr__(
            self,
            "description",
            self.description.strip(),
        )

    @property
    def source_title_keys(self) -> Tuple[str, ...]:
        return tuple(
            title.casefold()
            for title in self.source_titles
        )


def _default_request_merge_rules() -> Tuple[
    RequestMergeRule,
    ...,
]:
    """
    Load the approved merge catalog lazily.

    The lazy import avoids a circular import because the catalog imports
    RequestMergeRule from this module.
    """

    from src.evidence_requests.request_merge_catalog import (
        DEFAULT_REQUEST_MERGE_RULES,
    )

    return DEFAULT_REQUEST_MERGE_RULES


def _default_suppress_titles() -> Tuple[str, ...]:
    """
    Load the approved suppression catalog lazily.

    Keeping catalog data outside the optimizer allows the merge catalog to
    grow without expanding the optimizer engine itself.
    """

    from src.evidence_requests.request_merge_catalog import (
        DEFAULT_SUPPRESS_TITLES,
    )

    return DEFAULT_SUPPRESS_TITLES


@dataclass(frozen=True, slots=True)
class RequestOptimizerOptions:
    """
    Conservative optimizer configuration.

    The optimizer is intentionally explicit rather than fuzzy. It only
    merges titles listed in approved rules and only suppresses generic
    requests when every mapped control is already covered elsewhere.
    """

    request_prefix: str = "DRL"

    high_priority_reuse_threshold: int = 5

    medium_priority_reuse_threshold: int = 2

    suppress_titles: Tuple[str, ...] = field(
        default_factory=_default_suppress_titles
    )

    merge_rules: Tuple[RequestMergeRule, ...] = field(
        default_factory=_default_request_merge_rules
    )

    def __post_init__(self) -> None:
        prefix = self.request_prefix.strip()

        if not prefix:
            raise RequestOptimizerError(
                "RequestOptimizerOptions.request_prefix cannot be blank."
            )

        if self.high_priority_reuse_threshold < 1:
            raise RequestOptimizerError(
                "high_priority_reuse_threshold must be at least 1."
            )

        if self.medium_priority_reuse_threshold < 1:
            raise RequestOptimizerError(
                "medium_priority_reuse_threshold must be at least 1."
            )

        if (
            self.high_priority_reuse_threshold
            < self.medium_priority_reuse_threshold
        ):
            raise RequestOptimizerError(
                "high_priority_reuse_threshold cannot be lower than "
                "medium_priority_reuse_threshold."
            )

        suppress_titles = tuple(
            title.strip()
            for title in self.suppress_titles
            if title.strip()
        )

        object.__setattr__(
            self,
            "request_prefix",
            prefix,
        )

        object.__setattr__(
            self,
            "suppress_titles",
            suppress_titles,
        )

        self._validate_merge_rules()

    def _validate_merge_rules(self) -> None:
        title_to_package: Dict[str, str] = {}

        for rule in self.merge_rules:
            for title_key in rule.source_title_keys:
                existing = title_to_package.get(
                    title_key
                )

                if (
                    existing is not None
                    and existing.casefold()
                    != rule.package_title.casefold()
                ):
                    raise RequestOptimizerError(
                        "A source title cannot belong to more than "
                        "one merge package: "
                        f"{title_key!r}."
                    )

                title_to_package[
                    title_key
                ] = rule.package_title


class RequestOptimizer:
    """
    Convert a raw generated DRL into a smaller assessor-friendly DRL.

    Safety invariants:
      - the input collection is never mutated;
      - every unique control mapping is preserved;
      - generic requests are suppressed only when they add no unique control;
      - merges occur only through explicit approved rules;
      - request IDs are regenerated deterministically;
      - workflow-progressed requests are rejected rather than silently merged.
    """

    def __init__(
        self,
        options: RequestOptimizerOptions | None = None,
    ) -> None:
        self.options = (
            options
            or RequestOptimizerOptions()
        )

    def optimize(
        self,
        collection: DocumentationRequestCollection,
    ) -> DocumentationRequestCollection:
        self._validate_collection_state(
            collection
        )

        original_control_keys = (
            self._collection_control_keys(
                collection.requests
            )
        )

        working = [
            self._copy_request(request)
            for request in collection.requests
        ]

        working = self._apply_merge_rules(
            working
        )

        working = self._suppress_redundant_generic_requests(
            working
        )

        working = sorted(
            working,
            key=lambda request: (
                request.requested_item.casefold(),
                request.evidence_type.value.casefold(),
                tuple(
                    control.control_id.casefold()
                    for control in request.controls
                ),
            ),
        )

        optimized_requests = [
            self._with_request_id(
                request,
                sequence=index,
            )
            for index, request in enumerate(
                working,
                start=1,
            )
        ]

        optimized = DocumentationRequestCollection(
            framework_id=collection.framework_id,
            engagement_name=collection.engagement_name,
            organization_name=collection.organization_name,
            assessor_organization=(
                collection.assessor_organization
            ),
            engagement_start_date=(
                collection.engagement_start_date
            ),
            requests=optimized_requests,
            notes=collection.notes,
        )

        optimized_control_keys = (
            self._collection_control_keys(
                optimized.requests
            )
        )

        if optimized_control_keys != original_control_keys:
            missing = sorted(
                original_control_keys
                - optimized_control_keys
            )

            added = sorted(
                optimized_control_keys
                - original_control_keys
            )

            raise RequestOptimizerError(
                "Optimization changed control coverage. "
                f"Missing={missing!r}; Added={added!r}."
            )

        return optimized

    def _apply_merge_rules(
        self,
        requests: Sequence[
            DocumentationRequest
        ],
    ) -> List[DocumentationRequest]:
        remaining = list(
            requests
        )

        for rule in self.options.merge_rules:
            matches = [
                request
                for request in remaining
                if (
                    request.requested_item
                    .casefold()
                    in rule.source_title_keys
                )
            ]

            if len(matches) < 2:
                continue

            match_ids = {
                id(request)
                for request in matches
            }

            remaining = [
                request
                for request in remaining
                if id(request) not in match_ids
            ]

            remaining.append(
                self._merge_requests(
                    matches,
                    rule,
                )
            )

        return remaining

    def _merge_requests(
        self,
        requests: Sequence[
            DocumentationRequest
        ],
        rule: RequestMergeRule,
    ) -> DocumentationRequest:
        controls = self._deduplicate_controls(
            control
            for request in requests
            for control in request.controls
        )

        descriptions = self._deduplicate_text(
            request.description
            for request in requests
            if request.description.strip()
        )

        description = rule.description

        if descriptions:
            source_description = " | ".join(
                descriptions
            )

            if description:
                description = (
                    f"{description} Source wording: "
                    f"{source_description}"
                )
            else:
                description = source_description

        priority = self._highest_priority(
            (
                request.priority
                for request in requests
            ),
            reuse_count=len(controls),
        )

        return DocumentationRequest(
            request_id="TEMP",
            requested_item=rule.package_title,
            evidence_type=rule.evidence_type,
            priority=priority,
            controls=controls,
            description=description,
            review_status=(
                DocumentationRequestStatus.NOT_REQUESTED
            ),
            generated=True,
        )

    def _suppress_redundant_generic_requests(
        self,
        requests: Sequence[
            DocumentationRequest
        ],
    ) -> List[DocumentationRequest]:
        suppress_keys = {
            title.casefold()
            for title in self.options.suppress_titles
        }

        result: List[
            DocumentationRequest
        ] = []

        for index, request in enumerate(
            requests
        ):
            if (
                request.requested_item.casefold()
                not in suppress_keys
            ):
                result.append(
                    request
                )
                continue

            request_control_keys = {
                control.key
                for control in request.controls
            }

            other_control_keys = set()

            for other_index, other in enumerate(
                requests
            ):
                if other_index == index:
                    continue

                other_control_keys.update(
                    control.key
                    for control in other.controls
                )

            if request_control_keys.issubset(
                other_control_keys
            ):
                continue

            result.append(
                request
            )

        return result

    def _with_request_id(
        self,
        request: DocumentationRequest,
        *,
        sequence: int,
    ) -> DocumentationRequest:
        return DocumentationRequest(
            request_id=(
                f"{self.options.request_prefix}-"
                f"{sequence:03d}"
            ),
            requested_item=request.requested_item,
            evidence_type=request.evidence_type,
            priority=request.priority,
            controls=list(
                request.controls
            ),
            description=request.description,
            submitted=request.submitted,
            date_submitted=request.date_submitted,
            current_version=request.current_version,
            file_name=request.file_name,
            evidence_location=request.evidence_location,
            review_status=request.review_status,
            date_reviewed=request.date_reviewed,
            reviewer=request.reviewer,
            comments=request.comments,
            client_poc=request.client_poc,
            due_date=request.due_date,
            generated=request.generated,
        )

    @staticmethod
    def _copy_request(
        request: DocumentationRequest,
    ) -> DocumentationRequest:
        return DocumentationRequest(
            request_id=request.request_id,
            requested_item=request.requested_item,
            evidence_type=request.evidence_type,
            priority=request.priority,
            controls=list(
                request.controls
            ),
            description=request.description,
            submitted=request.submitted,
            date_submitted=request.date_submitted,
            current_version=request.current_version,
            file_name=request.file_name,
            evidence_location=request.evidence_location,
            review_status=request.review_status,
            date_reviewed=request.date_reviewed,
            reviewer=request.reviewer,
            comments=request.comments,
            client_poc=request.client_poc,
            due_date=request.due_date,
            generated=request.generated,
        )

    def _highest_priority(
        self,
        priorities: Iterable[
            DocumentationRequestPriority
        ],
        *,
        reuse_count: int,
    ) -> DocumentationRequestPriority:
        rank = {
            DocumentationRequestPriority.LOW: 1,
            DocumentationRequestPriority.MEDIUM: 2,
            DocumentationRequestPriority.HIGH: 3,
        }

        existing = max(
            priorities,
            key=lambda priority:
                rank[priority],
        )

        calculated = self._priority_for_reuse(
            reuse_count
        )

        return max(
            (
                existing,
                calculated,
            ),
            key=lambda priority:
                rank[priority],
        )

    def _priority_for_reuse(
        self,
        reuse_count: int,
    ) -> DocumentationRequestPriority:
        if (
            reuse_count
            >= self.options
            .high_priority_reuse_threshold
        ):
            return (
                DocumentationRequestPriority.HIGH
            )

        if (
            reuse_count
            >= self.options
            .medium_priority_reuse_threshold
        ):
            return (
                DocumentationRequestPriority.MEDIUM
            )

        return DocumentationRequestPriority.LOW

    @staticmethod
    def _deduplicate_controls(
        controls: Iterable[
            DocumentationRequestControl
        ],
    ) -> List[
        DocumentationRequestControl
    ]:
        result: List[
            DocumentationRequestControl
        ] = []

        seen = set()

        for control in controls:
            if control.key in seen:
                continue

            seen.add(
                control.key
            )

            result.append(
                control
            )

        return sorted(
            result,
            key=lambda control: (
                control.framework_id.casefold(),
                control.control_id.casefold(),
            ),
        )

    @staticmethod
    def _deduplicate_text(
        values: Iterable[str],
    ) -> List[str]:
        result: List[str] = []
        seen = set()

        for value in values:
            text = value.strip()

            if not text:
                continue

            key = text.casefold()

            if key in seen:
                continue

            seen.add(
                key
            )

            result.append(
                text
            )

        return result

    @staticmethod
    def _collection_control_keys(
        requests: Sequence[
            DocumentationRequest
        ],
    ) -> set[
        Tuple[str, str]
    ]:
        return {
            control.key
            for request in requests
            for control in request.controls
        }

    @staticmethod
    def _validate_collection_state(
        collection: DocumentationRequestCollection,
    ) -> None:
        for request in collection.requests:
            if not request.generated:
                raise RequestOptimizerError(
                    "Only generated DRL requests can be optimized. "
                    f"Request {request.request_id!r} is not generated."
                )

            if request.submitted:
                raise RequestOptimizerError(
                    "Submitted DRL requests cannot be optimized. "
                    f"Request {request.request_id!r} has already "
                    "been submitted."
                )

            if (
                request.review_status
                != DocumentationRequestStatus.NOT_REQUESTED
            ):
                raise RequestOptimizerError(
                    "Only untouched generated DRLs can be optimized. "
                    f"Request {request.request_id!r} has status "
                    f"{request.review_status.value!r}."
                )