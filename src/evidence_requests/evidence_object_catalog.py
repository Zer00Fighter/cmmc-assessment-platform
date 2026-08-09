from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, Tuple

from src.evidence_requests.evidence_object import (
    EvidenceCategory,
    EvidenceObject,
)


class EvidenceObjectCatalogError(ValueError):
    """Raised when Evidence Object Catalog data is invalid."""


@dataclass(frozen=True, slots=True)
class EvidenceObjectCatalogStatistics:
    """Calculated Evidence Object Catalog statistics."""

    object_count: int
    category_count: int
    alias_count: int


class EvidenceObjectCatalog:
    """
    Framework-independent catalog of logical Evidence Objects.

    The catalog stores and retrieves evidence knowledge only. It does not
    contain framework mappings, control mappings, organization ownership,
    DRL workflow state, optimization rules, package definitions, fuzzy
    matching, or resolver logic.

    Identity invariants:

        Evidence ID      -> exactly one EvidenceObject
        Canonical name   -> exactly one EvidenceObject
        Alias            -> exactly one EvidenceObject
    """

    def __init__(
        self,
        objects: Iterable[EvidenceObject] = (),
    ) -> None:
        self._by_id: Dict[str, EvidenceObject] = {}
        self._by_name: Dict[str, EvidenceObject] = {}

        for evidence in tuple(objects):
            self._register(evidence)

        self._objects: Tuple[EvidenceObject, ...] = tuple(
            sorted(
                self._by_id.values(),
                key=lambda item: (
                    item.canonical_name.casefold(),
                    item.evidence_id.casefold(),
                ),
            )
        )

    def __len__(self) -> int:
        return len(self._objects)

    def __iter__(self) -> Iterator[EvidenceObject]:
        return iter(self._objects)

    @property
    def count(self) -> int:
        return len(self._objects)

    @property
    def objects(self) -> Tuple[EvidenceObject, ...]:
        return self._objects

    @property
    def statistics(self) -> EvidenceObjectCatalogStatistics:
        categories = {
            evidence.category
            for evidence in self._objects
        }

        alias_count = sum(
            len(evidence.aliases)
            for evidence in self._objects
        )

        return EvidenceObjectCatalogStatistics(
            object_count=len(self._objects),
            category_count=len(categories),
            alias_count=alias_count,
        )

    def get_by_id(
        self,
        evidence_id: str,
    ) -> EvidenceObject:
        key = self._normalize_key(evidence_id)

        if not key:
            raise EvidenceObjectCatalogError(
                "Evidence ID cannot be blank."
            )

        try:
            return self._by_id[key]
        except KeyError as error:
            raise EvidenceObjectCatalogError(
                "Evidence Object not found by ID: "
                f"{str(evidence_id).strip()}"
            ) from error

    def get_by_name(
        self,
        name: str,
    ) -> EvidenceObject:
        key = self._normalize_key(name)

        if not key:
            raise EvidenceObjectCatalogError(
                "Evidence name cannot be blank."
            )

        try:
            return self._by_name[key]
        except KeyError as error:
            raise EvidenceObjectCatalogError(
                "Evidence Object not found by name: "
                f"{str(name).strip()}"
            ) from error

    def find_by_name(
        self,
        name: str,
    ) -> EvidenceObject | None:
        """
        Return an exact canonical-name or alias match, otherwise None.

        Matching is intentionally deterministic and not fuzzy.
        """

        key = self._normalize_key(name)

        if not key:
            return None

        return self._by_name.get(key)

    def for_category(
        self,
        category: EvidenceCategory,
    ) -> Tuple[EvidenceObject, ...]:
        return tuple(
            evidence
            for evidence in self._objects
            if evidence.category == category
        )

    def contains_id(
        self,
        evidence_id: str,
    ) -> bool:
        key = self._normalize_key(evidence_id)
        return bool(key) and key in self._by_id

    def contains_name(
        self,
        name: str,
    ) -> bool:
        key = self._normalize_key(name)
        return bool(key) and key in self._by_name

    def _register(
        self,
        evidence: EvidenceObject,
    ) -> None:
        if not isinstance(evidence, EvidenceObject):
            raise EvidenceObjectCatalogError(
                "EvidenceObjectCatalog entries must be "
                "EvidenceObject instances."
            )

        id_key = self._normalize_key(
            evidence.evidence_id
        )

        if id_key in self._by_id:
            raise EvidenceObjectCatalogError(
                "Duplicate Evidence Object ID: "
                f"{evidence.evidence_id}"
            )

        names = (
            evidence.canonical_name,
            *evidence.aliases,
        )

        for name in names:
            name_key = self._normalize_key(name)
            existing = self._by_name.get(name_key)

            if existing is not None:
                raise EvidenceObjectCatalogError(
                    "Duplicate or ambiguous Evidence Object name: "
                    f"{name!r}; already assigned to "
                    f"{existing.evidence_id!r}."
                )

        self._by_id[id_key] = evidence

        for name in names:
            self._by_name[
                self._normalize_key(name)
            ] = evidence

    @staticmethod
    def _normalize_key(
        value: str,
    ) -> str:
        return str(value).strip().casefold()