from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCENARIO_DIR = ROOT / "data" / "scenarios"

from tools.analytics import summarize_window


def inspect(name: str, minute: int) -> dict:
    df = pd.read_csv(SCENARIO_DIR / f"{name}.csv")
    return summarize_window(df, minute, window_minutes=10)


def main() -> None:
    checks = [
        ("sepsis_onset", 25, "sepsis_triad"),
        ("compensatory_shock", 30, "compensatory_tachycardia"),
        ("respiratory_deterioration", 30, "desaturation_trend"),
        ("stable_postop", 30, None),
    ]

    failures = []
    for scenario, minute, expected_pattern in checks:
        summary = inspect(scenario, minute)
        patterns = {item["pattern"] for item in summary["detected_patterns"]}
        print(
            f"{scenario}@{minute}: severity={summary['severity_hint']} news2={summary['derived_metrics']['news2']} "
            f"shock_index={summary['derived_metrics']['shock_index']} map={summary['derived_metrics']['map']} "
            f"patterns={sorted(patterns)}"
        )

        if expected_pattern and expected_pattern not in patterns:
            failures.append(f"{scenario} missing pattern {expected_pattern}")
        if scenario == "stable_postop" and summary["severity_hint"] != "INFO":
            failures.append("stable_postop should remain INFO")

    if failures:
        raise SystemExit("Verification failed: " + "; ".join(failures))

    print("Scenario verification passed.")


if __name__ == "__main__":
    main()
