from pathlib import Path

from src.scoring.scoring_compiler import ScoringCompiler


ROOT = Path(__file__).resolve().parent


def main() -> None:
    controls_csv = (
        ROOT
        / "data"
        / "controls"
        / "cmmc_level2_controls.csv"
    )

    output_csv = (
        ROOT
        / "data"
        / "scoring"
        / "scoring_weights.csv"
    )

    print("Compiling official CMMC Level 2 scoring table...")

    compiler = ScoringCompiler(
        controls_csv=controls_csv,
        output_csv=output_csv,
    )

    weights = compiler.compile()

    print(f"Scoring rows generated: {len(weights)}")
    print(f"Output: {output_csv}")
    print("Scoring compilation completed successfully.")


if __name__ == "__main__":
    main()