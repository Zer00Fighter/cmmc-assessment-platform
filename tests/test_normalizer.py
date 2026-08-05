from src.compiler.content_parser import (
    ParsedObjective,
    ParsedRequirement,
)
from src.compiler.normalizer import TextNormalizer


def test_normalize_unicode() -> None:
    normalizer = TextNormalizer()

    result = normalizer.normalize_unicode(
        '“Authorized” access — required'
    )

    assert result == '"Authorized" access - required'


def test_remove_soft_hyphen() -> None:
    normalizer = TextNormalizer()

    result = normalizer.remove_soft_hyphens(
        "autho\u00adrized"
    )

    assert result == "authorized"


def test_remove_headers_and_page_numbers() -> None:
    normalizer = TextNormalizer()

    text = (
        "CMMC Assessment Guide - Level 2\n"
        "Version 2.13 | September 2024\n"
        "14\n"
        "Limit system access."
    )

    result = normalizer.remove_headers_and_footers(text)

    assert result == "Limit system access."


def test_join_wrapped_lines() -> None:
    normalizer = TextNormalizer()

    text = (
        "Limit system access to authorized users,\n"
        "processes acting on behalf of users,\n"
        "and authorized devices."
    )

    result = normalizer.join_wrapped_lines(text)

    assert result == (
        "Limit system access to authorized users, "
        "processes acting on behalf of users, "
        "and authorized devices."
    )


def test_join_hyphenated_word() -> None:
    normalizer = TextNormalizer()

    text = "autho-\nrized users"

    result = normalizer.join_wrapped_lines(text)

    assert result == "authorized users"


def test_normalize_statement_adds_period() -> None:
    normalizer = TextNormalizer()

    result = normalizer.normalize_statement(
        "Limit system access"
    )

    assert result == "Limit system access."


def test_normalize_references_removes_duplicates() -> None:
    normalizer = TextNormalizer()

    references = [
        "NIST SP 800-171 Rev. 2 3.1.1",
        "NIST SP 800-171 Rev. 2 3.1.1",
        "FAR Clause 52.204-21",
    ]

    result = normalizer.normalize_references(references)

    assert result == [
        "NIST SP 800-171 Rev. 2 3.1.1",
        "FAR Clause 52.204-21",
    ]


def test_normalize_requirement() -> None:
    normalizer = TextNormalizer()

    requirement = ParsedRequirement(
        requirement_id="AC.L2-3.1.1",
        domain_code="AC",
        title=" AUTHORIZED ACCESS CONTROL ",
        statement="Limit system access",
        objectives=[
            ParsedObjective(
                requirement_id="AC.L2-3.1.1",
                objective_id="A",
                objective_text=(
                    "authorized users are identified"
                ),
            )
        ],
        examine_objects=[
            " Access control policy ",
            "Access control policy",
        ],
        interview_objects=[
            "System administrators",
        ],
        test_objects=[
            "Account management mechanisms",
        ],
        key_references=[
            " NIST SP 800-171 Rev. 2 3.1.1 ",
        ],
        source_page_start=22,
        source_page_end=24,
    )

    result = normalizer.normalize_requirement(
        requirement
    )

    assert result.title == "AUTHORIZED ACCESS CONTROL"
    assert result.statement == "Limit system access."
    assert result.objectives[0].objective_id == "a"
    assert result.examine_objects == [
        "Access control policy"
    ]
    assert result.key_references == [
        "NIST SP 800-171 Rev. 2 3.1.1"
    ]