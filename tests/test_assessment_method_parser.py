from __future__ import annotations

import pytest

from src.evidence_requests.assessment_method_parser import (
    AssessmentMethod,
    AssessmentMethodParser,
    AssessmentMethodParserError,
    AssessmentMethodType,
    AssessmentObject,
    AssessmentObjectType,
)


@pytest.fixture
def parser() -> AssessmentMethodParser:
    return AssessmentMethodParser()


def test_parse_empty_text(
    parser: AssessmentMethodParser,
) -> None:
    method = parser.parse(
        AssessmentMethodType.EXAMINE,
        "",
    )

    assert isinstance(
        method,
        AssessmentMethod,
    )

    assert (
        method.method_type
        == AssessmentMethodType.EXAMINE
    )

    assert method.objects == ()
    assert method.object_count == 0


def test_parse_none_text(
    parser: AssessmentMethodParser,
) -> None:
    method = parser.parse(
        AssessmentMethodType.EXAMINE,
        None,
    )

    assert method.objects == ()
    assert method.raw_text == ""


def test_parse_method_type_from_string(
    parser: AssessmentMethodParser,
) -> None:
    method = parser.parse(
        "examine",
        "access control policy",
    )

    assert (
        method.method_type
        == AssessmentMethodType.EXAMINE
    )


def test_unknown_method_type_rejected(
    parser: AssessmentMethodParser,
) -> None:
    with pytest.raises(
        AssessmentMethodParserError
    ):
        parser.parse(
            "DO_SOMETHING",
            "access control policy",
        )


def test_tokenize_semicolon_list(
    parser: AssessmentMethodParser,
) -> None:
    tokens = parser.tokenize(
        "access control policy; "
        "system security plan; "
        "audit records"
    )

    assert tokens == [
        "access control policy",
        "system security plan",
        "audit records",
    ]


def test_tokenize_newline_list(
    parser: AssessmentMethodParser,
) -> None:
    tokens = parser.tokenize(
        "access control policy\n"
        "system security plan\n"
        "audit records"
    )

    assert tokens == [
        "access control policy",
        "system security plan",
        "audit records",
    ]


def test_tokenize_bullet_list(
    parser: AssessmentMethodParser,
) -> None:
    tokens = parser.tokenize(
        "• access control policy "
        "• system security plan "
        "• audit records"
    )

    assert tokens == [
        "access control policy",
        "system security plan",
        "audit records",
    ]


def test_tokenize_select_from_wrapper(
    parser: AssessmentMethodParser,
) -> None:
    tokens = parser.tokenize(
        "[SELECT FROM: "
        "access control policy; "
        "system security plan; "
        "audit records]"
    )

    assert tokens == [
        "access control policy",
        "system security plan",
        "audit records",
    ]


def test_policy_classification(
    parser: AssessmentMethodParser,
) -> None:
    result = parser.classify(
        "access control policy"
    )

    assert (
        result
        == AssessmentObjectType.POLICY
    )


def test_procedure_classification(
    parser: AssessmentMethodParser,
) -> None:
    result = parser.classify(
        "procedures addressing account management"
    )

    assert (
        result
        == AssessmentObjectType.PROCEDURE
    )


def test_system_security_plan_classification(
    parser: AssessmentMethodParser,
) -> None:
    result = parser.classify(
        "system security plan"
    )

    assert (
        result
        == AssessmentObjectType.SYSTEM_SECURITY_PLAN
    )


def test_ssp_alias_classification(
    parser: AssessmentMethodParser,
) -> None:
    result = parser.classify(
        "SSP"
    )

    assert (
        result
        == AssessmentObjectType.SYSTEM_SECURITY_PLAN
    )


def test_poam_classification(
    parser: AssessmentMethodParser,
) -> None:
    assert (
        parser.classify("POA&M")
        == AssessmentObjectType.POAM
    )

    assert (
        parser.classify(
            "plan of action and milestones"
        )
        == AssessmentObjectType.POAM
    )


def test_configuration_classification(
    parser: AssessmentMethodParser,
) -> None:
    assert (
        parser.classify(
            "system configuration settings"
        )
        == AssessmentObjectType.CONFIGURATION
    )


def test_configuration_baseline_classification(
    parser: AssessmentMethodParser,
) -> None:
    assert (
        parser.classify(
            "configuration baseline"
        )
        == AssessmentObjectType.CONFIGURATION_BASELINE
    )


def test_log_classification(
    parser: AssessmentMethodParser,
) -> None:
    assert (
        parser.classify(
            "audit logs"
        )
        == AssessmentObjectType.LOG
    )


def test_inventory_classification(
    parser: AssessmentMethodParser,
) -> None:
    assert (
        parser.classify(
            "system inventory"
        )
        == AssessmentObjectType.INVENTORY
    )


def test_diagram_classification(
    parser: AssessmentMethodParser,
) -> None:
    assert (
        parser.classify(
            "network diagram"
        )
        == AssessmentObjectType.DIAGRAM
    )


def test_report_classification(
    parser: AssessmentMethodParser,
) -> None:
    assert (
        parser.classify(
            "vulnerability scan report"
        )
        == AssessmentObjectType.REPORT
    )


def test_training_record_classification(
    parser: AssessmentMethodParser,
) -> None:
    assert (
        parser.classify(
            "security awareness training records"
        )
        == AssessmentObjectType.TRAINING_RECORD
    )


def test_personnel_record_classification(
    parser: AssessmentMethodParser,
) -> None:
    assert (
        parser.classify(
            "personnel background check records"
        )
        == AssessmentObjectType.PERSONNEL_RECORD
    )


def test_interview_defaults_to_interview_subject(
    parser: AssessmentMethodParser,
) -> None:
    result = parser.classify(
        "system administrators",
        AssessmentMethodType.INTERVIEW,
    )

    assert (
        result
        == AssessmentObjectType.INTERVIEW_SUBJECT
    )


def test_test_method_defaults_to_test_target(
    parser: AssessmentMethodParser,
) -> None:
    result = parser.classify(
        "mechanisms implementing access restrictions",
        AssessmentMethodType.TEST,
    )

    assert (
        result
        == AssessmentObjectType.TEST_TARGET
    )


def test_unknown_examine_object_defaults_to_other(
    parser: AssessmentMethodParser,
) -> None:
    result = parser.classify(
        "miscellaneous supporting information",
        AssessmentMethodType.EXAMINE,
    )

    assert (
        result
        == AssessmentObjectType.OTHER
    )


def test_normalize_access_control_policy_title(
    parser: AssessmentMethodParser,
) -> None:
    assert (
        parser.normalize_title(
            "access control policy"
        )
        == "Access Control Policy"
    )


def test_normalize_procedure_title(
    parser: AssessmentMethodParser,
) -> None:
    assert (
        parser.normalize_title(
            "procedures addressing account management"
        )
        == "Account Management Procedures"
    )


def test_normalize_ssp_title(
    parser: AssessmentMethodParser,
) -> None:
    assert (
        parser.normalize_title("SSP")
        == "System Security Plan"
    )


def test_normalize_poam_title(
    parser: AssessmentMethodParser,
) -> None:
    assert (
        parser.normalize_title("POA&M")
        == "Plan of Action and Milestones"
    )


def test_policy_canonical_id(
    parser: AssessmentMethodParser,
) -> None:
    canonical_id = parser.canonical_id(
        "access control policy"
    )

    assert (
        canonical_id
        == "EVIDENCE_POLICY_ACCESS_CONTROL_POLICY"
    )


def test_ssp_canonical_id_is_stable(
    parser: AssessmentMethodParser,
) -> None:
    assert (
        parser.canonical_id("SSP")
        == "EVIDENCE_SYSTEM_SECURITY_PLAN"
    )

    assert (
        parser.canonical_id(
            "system security plan"
        )
        == "EVIDENCE_SYSTEM_SECURITY_PLAN"
    )


def test_poam_canonical_id_is_stable(
    parser: AssessmentMethodParser,
) -> None:
    assert (
        parser.canonical_id("POA&M")
        == "EVIDENCE_POAM"
    )

    assert (
        parser.canonical_id(
            "plan of action and milestones"
        )
        == "EVIDENCE_POAM"
    )


def test_parse_examine_method(
    parser: AssessmentMethodParser,
) -> None:
    method = parser.parse(
        AssessmentMethodType.EXAMINE,
        (
            "[SELECT FROM: "
            "access control policy; "
            "procedures addressing account management; "
            "system security plan]"
        ),
    )

    assert method.object_count == 3

    assert [
        item.object_type
        for item in method.objects
    ] == [
        AssessmentObjectType.POLICY,
        AssessmentObjectType.PROCEDURE,
        AssessmentObjectType.SYSTEM_SECURITY_PLAN,
    ]


def test_parse_examine_titles(
    parser: AssessmentMethodParser,
) -> None:
    method = parser.parse(
        AssessmentMethodType.EXAMINE,
        (
            "access control policy; "
            "procedures addressing account management; "
            "system security plan"
        ),
    )

    assert [
        item.title
        for item in method.objects
    ] == [
        "Access Control Policy",
        "Account Management Procedures",
        "System Security Plan",
    ]


def test_parse_interview_method(
    parser: AssessmentMethodParser,
) -> None:
    method = parser.parse(
        AssessmentMethodType.INTERVIEW,
        (
            "personnel with account "
            "management responsibilities; "
            "system administrators"
        ),
    )

    assert method.object_count == 2

    assert all(
        item.object_type
        == AssessmentObjectType.INTERVIEW_SUBJECT
        for item in method.objects
    )


def test_parse_test_method(
    parser: AssessmentMethodParser,
) -> None:
    method = parser.parse(
        AssessmentMethodType.TEST,
        (
            "mechanisms implementing "
            "access control restrictions; "
            "account management mechanisms"
        ),
    )

    assert method.object_count == 2

    assert all(
        item.object_type
        == AssessmentObjectType.TEST_TARGET
        for item in method.objects
    )


def test_duplicate_objects_are_removed(
    parser: AssessmentMethodParser,
) -> None:
    method = parser.parse(
        AssessmentMethodType.EXAMINE,
        (
            "system security plan; "
            "SSP; "
            "system security plan"
        ),
    )

    assert method.object_count == 1

    assert (
        method.objects[0].canonical_id
        == "EVIDENCE_SYSTEM_SECURITY_PLAN"
    )


def test_canonical_ids_property(
    parser: AssessmentMethodParser,
) -> None:
    method = parser.parse(
        AssessmentMethodType.EXAMINE,
        (
            "access control policy; "
            "system security plan"
        ),
    )

    assert method.canonical_ids == (
        "EVIDENCE_POLICY_ACCESS_CONTROL_POLICY",
        "EVIDENCE_SYSTEM_SECURITY_PLAN",
    )


def test_assessment_object_validation() -> None:
    with pytest.raises(
        AssessmentMethodParserError
    ):
        AssessmentObject(
            canonical_id="",
            object_type=AssessmentObjectType.POLICY,
            title="Policy",
            raw_text="policy",
        )


def test_parse_many(
    parser: AssessmentMethodParser,
) -> None:
    methods = parser.parse_many(
        AssessmentMethodType.EXAMINE,
        [
            "access control policy",
            "system security plan",
        ],
    )

    assert len(methods) == 2

    assert (
        methods[0].objects[0].object_type
        == AssessmentObjectType.POLICY
    )

    assert (
        methods[1].objects[0].object_type
        == AssessmentObjectType.SYSTEM_SECURITY_PLAN
    )


def test_non_cmmc_assessment_content(
    parser: AssessmentMethodParser,
) -> None:
    method = parser.parse(
        AssessmentMethodType.EXAMINE,
        (
            "payment card security policy; "
            "authentication configuration; "
            "audit logs"
        ),
    )

    assert method.object_count == 3

    assert [
        item.object_type
        for item in method.objects
    ] == [
        AssessmentObjectType.POLICY,
        AssessmentObjectType.CONFIGURATION,
        AssessmentObjectType.LOG,
    ]


def test_canonical_id_is_deterministic(
    parser: AssessmentMethodParser,
) -> None:
    first = parser.canonical_id(
        "network diagram"
    )

    second = parser.canonical_id(
        "network diagram"
    )

    assert first == second


def test_case_variations_produce_same_policy_id(
    parser: AssessmentMethodParser,
) -> None:
    first = parser.canonical_id(
        "Access Control Policy"
    )

    second = parser.canonical_id(
        "access control policy"
    )

    assert first == second


def test_method_raw_text_is_preserved(
    parser: AssessmentMethodParser,
) -> None:
    raw = (
        "[SELECT FROM: "
        "access control policy; "
        "system security plan]"
    )

    method = parser.parse(
        AssessmentMethodType.EXAMINE,
        raw,
    )

    assert method.raw_text == raw