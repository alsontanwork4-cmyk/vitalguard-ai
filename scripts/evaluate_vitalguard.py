from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.analytics import summarize_window
from tools.vitaldb_adapter import normalize_vitaldb_csv_with_metadata

SCENARIO_DIR = ROOT / "data" / "scenarios"
REPORT_DIR = ROOT / "data" / "eval_reports"
REAL_VITALDB_CASE = ROOT / "data" / "vitaldb_case_4096.csv"


def _find_first_alert(df: pd.DataFrame) -> dict:
    for minute in range(1, len(df)):
        summary = summarize_window(df, minute, window_minutes=10)
        patterns = [item["pattern"] for item in summary["detected_patterns"]]
        if summary["severity_hint"] != "INFO" or patterns:
            return {
                "alert_minute": minute,
                "severity": summary["severity_hint"],
                "patterns": patterns,
                "news2": summary["derived_metrics"]["news2"],
                "shock_index": summary["derived_metrics"]["shock_index"],
                "map": summary["derived_metrics"]["map"],
            }
    final = summarize_window(df, len(df) - 1, window_minutes=10)
    return {
        "alert_minute": None,
        "severity": final["severity_hint"],
        "patterns": [item["pattern"] for item in final["detected_patterns"]],
        "news2": final["derived_metrics"]["news2"],
        "shock_index": final["derived_metrics"]["shock_index"],
        "map": final["derived_metrics"]["map"],
    }


def _find_first_pattern(df: pd.DataFrame, expected_pattern: str) -> int | None:
    for minute in range(1, len(df)):
        summary = summarize_window(df, minute, window_minutes=10)
        patterns = [item["pattern"] for item in summary["detected_patterns"]]
        if expected_pattern in patterns:
            return minute
    return None


def _evaluate_scenario(name: str, expected_pattern: str | None, latest_expected_minute: int | None) -> dict:
    df = pd.read_csv(SCENARIO_DIR / f"{name}.csv")
    result = _find_first_alert(df)
    pattern_minute = _find_first_pattern(df, expected_pattern) if expected_pattern else None
    pattern_hit = expected_pattern is None or pattern_minute is not None
    timing_hit = latest_expected_minute is None or (
        result["alert_minute"] is not None and result["alert_minute"] <= latest_expected_minute
    )
    pattern_timing_hit = latest_expected_minute is None or expected_pattern is None or (
        pattern_minute is not None and pattern_minute <= latest_expected_minute
    )
    no_intervention_hit = expected_pattern is None and result["alert_minute"] is None

    return {
        "dataset": name,
        "kind": "scenario",
        "expected_pattern": expected_pattern,
        "latest_expected_minute": latest_expected_minute,
        "pattern_minute": pattern_minute,
        **result,
        "passed": bool(no_intervention_hit or (pattern_hit and timing_hit and pattern_timing_hit)),
    }


def _evaluate_real_vitaldb_case() -> dict:
    if not REAL_VITALDB_CASE.exists():
        return {
            "dataset": REAL_VITALDB_CASE.name,
            "kind": "vitaldb",
            "passed": False,
            "status": "missing",
            "message": "Run scripts/download_vitaldb_case.py first.",
        }

    normalized, metadata = normalize_vitaldb_csv_with_metadata(REAL_VITALDB_CASE)
    result = _find_first_alert(normalized)
    return {
        "dataset": REAL_VITALDB_CASE.name,
        "kind": "vitaldb",
        "status": "ok" if metadata["can_analyze"] else "recovery",
        "degraded_mode": metadata["degraded_mode"],
        "degradation_reasons": metadata["degradation_reasons"],
        "found_tracks": metadata["found_tracks"],
        "missing_required_signals": metadata["missing_required_signals"],
        **result,
        "passed": metadata["can_analyze"],
    }


def _evaluate_degraded_vitaldb_case() -> dict:
    if not REAL_VITALDB_CASE.exists():
        return {
            "dataset": "degraded_vitaldb_case_4096",
            "kind": "vitaldb_degraded",
            "passed": False,
            "status": "missing",
            "message": "Run scripts/download_vitaldb_case.py first.",
        }

    degraded_source = pd.read_csv(REAL_VITALDB_CASE)
    degraded_source["Solar8000/BT"] = float("nan")
    degraded_source.loc[degraded_source.index % 3 == 0, "Solar8000/NIBP_SBP"] = float("nan")
    degraded_source.loc[degraded_source.index % 3 == 0, "Solar8000/NIBP_DBP"] = float("nan")

    tmp_path = REPORT_DIR / "degraded_vitaldb_case_4096.csv"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    degraded_source.to_csv(tmp_path, index=False)

    normalized, metadata = normalize_vitaldb_csv_with_metadata(tmp_path)
    result = _find_first_alert(normalized)

    return {
        "dataset": tmp_path.name,
        "kind": "vitaldb_degraded",
        "status": "ok" if metadata["can_analyze"] else "recovery",
        "degraded_mode": metadata["degraded_mode"],
        "degradation_reasons": metadata["degradation_reasons"],
        "found_tracks": metadata["found_tracks"],
        "missing_required_signals": metadata["missing_required_signals"],
        "interpolated_signals": metadata["interpolated_signals"],
        "imputed_optional_signals": metadata["imputed_optional_signals"],
        **result,
        "passed": metadata["can_analyze"] and metadata["degraded_mode"],
    }


def _write_markdown_report(results: list[dict]) -> Path:
    report_path = REPORT_DIR / "vitalguard_evaluation.md"
    lines = [
        "# VitalGuard Evaluation Report",
        "",
        "| Dataset | Kind | Alert Minute | Severity | Expected Pattern | Pattern Minute | First Detected Patterns | Passed |",
        "| --- | --- | ---: | --- | --- | ---: | --- | --- |",
    ]

    for result in results:
        alert_minute = result.get("alert_minute")
        patterns = ", ".join(result.get("patterns", [])) or "-"
        expected_pattern = result.get("expected_pattern", "-") or "-"
        pattern_minute = result.get("pattern_minute")
        lines.append(
            f"| {result['dataset']} | {result['kind']} | {alert_minute if alert_minute is not None else '-'} "
            f"| {result.get('severity', result.get('status', '-'))} | {expected_pattern} "
            f"| {pattern_minute if pattern_minute is not None else '-'} | {patterns} | {result['passed']} |"
        )

    lines.extend(
        [
            "",
            "## Recovery Notes",
            "",
            "- Real VitalDB evaluation proves the loader can normalize a public case into the monitor schema.",
            "- Degraded VitalDB evaluation removes temperature and creates intermittent NIBP gaps to verify recovery mode.",
            "- Stable synthetic scenario is expected to remain INFO with no intervention.",
        ]
    )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = [
        _evaluate_scenario("sepsis_onset", "sepsis_triad", 30),
        _evaluate_scenario("compensatory_shock", "compensatory_tachycardia", 35),
        _evaluate_scenario("respiratory_deterioration", "desaturation_trend", 35),
        _evaluate_scenario("stable_postop", None, None),
        _evaluate_real_vitaldb_case(),
        _evaluate_degraded_vitaldb_case(),
    ]

    json_path = REPORT_DIR / "vitalguard_evaluation.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    markdown_path = _write_markdown_report(results)

    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    for result in results:
        print(
            f"{result['dataset']}: kind={result['kind']} passed={result['passed']} "
            f"severity={result.get('severity', result.get('status'))} "
            f"alert_minute={result.get('alert_minute')}"
        )


if __name__ == "__main__":
    main()
