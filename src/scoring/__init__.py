"""
CMMC Level 2 Scoring Package

This package contains:

- Scoring compiler
- Partial credit evaluator
- Scoring engine
- Scoring validator
"""

# ----------------------------------------------------------------------
# Compiler
# ----------------------------------------------------------------------

from .scoring_compiler import (
    ScoringCompiler,
    ScoringWeight,
)

# ----------------------------------------------------------------------
# Partial Credit
# ----------------------------------------------------------------------

from .partial_credit import (
    AssessmentFinding,
    PartialCreditError,
    PartialCreditEvaluator,
    PartialCreditResult,
    PartialCreditRule,
    PartialImplementationState,
)

# ----------------------------------------------------------------------
# Scoring Engine
# ----------------------------------------------------------------------

from .scoring_engine import (
    AssessmentScore,
    DomainScore,
    RequirementAssessment,
    RequirementScore,
    ScoringEngine,
    ScoringEngineError,
    ScoringRule,
)

# ----------------------------------------------------------------------
# Validator
# ----------------------------------------------------------------------

from .scoring_validator import (
    ScoringValidationError,
    ScoringValidationIssue,
    ScoringValidationReport,
    ScoringValidator,
)

__version__ = "1.0.0"

__all__ = [
    # Compiler
    "ScoringCompiler",
    "ScoringWeight",

    # Partial Credit
    "AssessmentFinding",
    "PartialCreditError",
    "PartialCreditEvaluator",
    "PartialCreditResult",
    "PartialCreditRule",
    "PartialImplementationState",

    # Engine
    "AssessmentScore",
    "DomainScore",
    "RequirementAssessment",
    "RequirementScore",
    "ScoringEngine",
    "ScoringEngineError",
    "ScoringRule",

    # Validator
    "ScoringValidationError",
    "ScoringValidationIssue",
    "ScoringValidationReport",
    "ScoringValidator",
]
