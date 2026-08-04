from pathlib import Path

from src.loaders.csv_loader import (
    load_controls,
    load_domains,
)


ROOT = Path(__file__).resolve().parent


def main() -> None:
    domains = load_domains(
        ROOT / "data" / "controls" / "domains.csv"
    )

    controls = load_controls(
        ROOT
        / "data"
        / "controls"
        / "cmmc_level2_controls.csv"
    )

    print(f"Loaded {len(domains)} domains")
    print(f"Loaded {len(controls)} controls")
    print(f"First control: {controls[0].requirement_id}")
    print("Sprint 2 data layer validation passed.")


if __name__ == "__main__":
    main()