from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


VITAL_COLUMNS = ["hr", "spo2", "sbp", "dbp", "temp_c", "rr", "etco2"]


@dataclass(frozen=True)
class SeverityScore:
    label: str
    rank: int


SEVERITY_RANK = {
    "INFO": SeverityScore("INFO", 0),
    "WARNING": SeverityScore("WARNING", 1),
    "CRITICAL": SeverityScore("CRITICAL", 2),
}


def compute_map(sbp: float, dbp: float) -> float:
    return round((sbp + 2 * dbp) / 3, 1)


def compute_shock_index(hr: float, sbp: float) -> float:
    if sbp <= 0:
        return 0.0
    return round(hr / sbp, 2)


def score_news2_row(row: pd.Series) -> int:
    score = 0

    rr = float(row["rr"])
    if rr <= 8:
        score += 3
    elif rr <= 11:
        score += 1
    elif rr <= 20:
        score += 0
    elif rr <= 24:
        score += 2
    else:
        score += 3

    spo2 = float(row["spo2"])
    if spo2 <= 91:
        score += 3
    elif spo2 <= 93:
        score += 2
    elif spo2 <= 95:
        score += 1

    temp_c = float(row["temp_c"])
    if temp_c <= 35.0:
        score += 3
    elif temp_c <= 36.0:
        score += 1
    elif temp_c <= 38.0:
        score += 0
    elif temp_c <= 39.0:
        score += 1
    else:
        score += 2

    sbp = float(row["sbp"])
    if sbp <= 90:
        score += 3
    elif sbp <= 100:
        score += 2
    elif sbp <= 110:
        score += 1
    elif sbp >= 220:
        score += 3

    hr = float(row["hr"])
    if hr <= 40:
        score += 3
    elif hr <= 50:
        score += 1
    elif hr <= 90:
        score += 0
    elif hr <= 110:
        score += 1
    elif hr <= 130:
        score += 2
    else:
        score += 3

    return score


def enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy()
    enriched["map"] = enriched.apply(
        lambda row: compute_map(float(row["sbp"]), float(row["dbp"])), axis=1
    )
    enriched["shock_index"] = enriched.apply(
        lambda row: compute_shock_index(float(row["hr"]), float(row["sbp"])), axis=1
    )
    enriched["news2"] = enriched.apply(score_news2_row, axis=1)
    enriched["qsofa_limited"] = (
        (enriched["rr"] >= 22).astype(int) + (enriched["sbp"] <= 100).astype(int)
    )
    return enriched


def _round_mapping(values: dict[str, float]) -> dict[str, float]:
    return {key: round(float(value), 2) for key, value in values.items()}


def _score_to_severity(news2: float, shock_index: float, map_value: float) -> str:
    if news2 >= 7 or shock_index >= 1.3 or map_value < 65:
        return "CRITICAL"
    if news2 >= 5 or shock_index >= 0.9:
        return "WARNING"
    return "INFO"


def _add_flag(flags: list[dict[str, Any]], severity: str, metric: str, message: str) -> None:
    flags.append({"severity": severity, "metric": metric, "message": message})


def detect_threshold_flags(latest: pd.Series) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    if float(latest["spo2"]) < 90:
        _add_flag(flags, "CRITICAL", "spo2", "SpO2 is below 90%, indicating severe hypoxemia.")
    elif float(latest["spo2"]) <= 94:
        _add_flag(flags, "WARNING", "spo2", "SpO2 is below the expected safe range.")

    if float(latest["sbp"]) <= 90:
        _add_flag(flags, "CRITICAL", "sbp", "Systolic blood pressure is at or below 90 mmHg.")
    elif float(latest["sbp"]) <= 100:
        _add_flag(flags, "WARNING", "sbp", "Systolic blood pressure is nearing hypotension.")

    if float(latest["map"]) < 65:
        _add_flag(flags, "CRITICAL", "map", "MAP is below 65 mmHg, suggesting poor organ perfusion.")

    if float(latest["rr"]) >= 25:
        _add_flag(flags, "CRITICAL", "rr", "Respiratory rate is 25 or higher.")
    elif float(latest["rr"]) >= 22:
        _add_flag(flags, "WARNING", "rr", "Respiratory rate is elevated and meets qSOFA respiratory criteria.")

    if float(latest["temp_c"]) >= 39.0:
        _add_flag(flags, "CRITICAL", "temp_c", "Temperature is 39.0C or higher.")
    elif float(latest["temp_c"]) >= 38.0:
        _add_flag(flags, "WARNING", "temp_c", "Temperature is febrile.")

    if float(latest["shock_index"]) >= 1.3:
        _add_flag(flags, "CRITICAL", "shock_index", "Shock index is above 1.3, consistent with severe shock.")
    elif float(latest["shock_index"]) >= 0.9:
        _add_flag(flags, "WARNING", "shock_index", "Shock index is above 0.9, consistent with early shock.")

    if float(latest["news2"]) >= 7:
        _add_flag(flags, "CRITICAL", "news2", "NEWS2 is 7 or higher.")
    elif float(latest["news2"]) >= 5:
        _add_flag(flags, "WARNING", "news2", "NEWS2 is 5 or higher.")
    elif float(latest["news2"]) >= 3:
        _add_flag(flags, "WARNING", "news2", "NEWS2 has reached the medium-risk range.")

    return flags


def detect_patterns(window: pd.DataFrame) -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    if len(window) < 3:
        return patterns

    latest = window.iloc[-1]
    prior = window.iloc[0]
    minutes = max(1, float(window["minute"].iloc[-1] - window["minute"].iloc[0]))

    hr_slope = (float(latest["hr"]) - float(prior["hr"])) / minutes
    sbp_slope = (float(latest["sbp"]) - float(prior["sbp"])) / minutes
    rr_slope = (float(latest["rr"]) - float(prior["rr"])) / minutes
    temp_slope = (float(latest["temp_c"]) - float(prior["temp_c"])) / minutes
    spo2_slope = (float(latest["spo2"]) - float(prior["spo2"])) / minutes
    news2_slope = (float(latest["news2"]) - float(prior["news2"])) / minutes
    shock_trend = float(latest["shock_index"]) - float(prior["shock_index"])

    if temp_slope >= 0.03 and hr_slope >= 0.4 and rr_slope >= 0.15 and float(latest["temp_c"]) >= 38.0:
        patterns.append(
            {
                "severity": "CRITICAL" if latest["qsofa_limited"] >= 2 else "WARNING",
                "pattern": "sepsis_triad",
                "message": "Temperature, heart rate, and respiratory rate are climbing together.",
            }
        )

    if hr_slope >= 0.6 and sbp_slope <= -0.25 and (
        shock_trend >= 0.08 or float(latest["shock_index"]) >= 0.75
    ):
        patterns.append(
            {
                "severity": "WARNING" if float(latest["sbp"]) > 90 else "CRITICAL",
                "pattern": "compensatory_tachycardia",
                "message": "Heart rate is rising faster than blood pressure can compensate, consistent with evolving shock.",
            }
        )

    if spo2_slope <= -0.08 and rr_slope >= 0.12:
        patterns.append(
            {
                "severity": "WARNING" if float(latest["spo2"]) >= 90 else "CRITICAL",
                "pattern": "desaturation_trend",
                "message": "SpO2 is drifting downward while respiratory rate climbs.",
            }
        )

    if news2_slope >= 0.08 and float(latest["news2"]) >= 5:
        patterns.append(
            {
                "severity": "WARNING" if float(latest["news2"]) < 7 else "CRITICAL",
                "pattern": "silent_deterioration",
                "message": "Composite NEWS2 risk is rising faster than single thresholds alone would show.",
            }
        )

    return patterns


def summarize_window(df: pd.DataFrame, cursor_minute: int, window_minutes: int = 10) -> dict[str, Any]:
    end_idx = min(cursor_minute, len(df) - 1)
    start_minute = max(0, end_idx - window_minutes + 1)
    window = enrich_dataframe(df.iloc[start_minute : end_idx + 1]).reset_index(drop=True)
    baseline = enrich_dataframe(df.iloc[: min(10, len(df))]).reset_index(drop=True)
    latest = window.iloc[-1]
    baseline_latest = baseline[VITAL_COLUMNS].mean(numeric_only=True)
    slopes = {}

    if len(window) > 1:
        minutes = max(1, float(window["minute"].iloc[-1] - window["minute"].iloc[0]))
        for column in VITAL_COLUMNS + ["news2", "shock_index", "map"]:
            slopes[column] = (float(window[column].iloc[-1]) - float(window[column].iloc[0])) / minutes
    else:
        for column in VITAL_COLUMNS + ["news2", "shock_index", "map"]:
            slopes[column] = 0.0

    rolling_means = {
        "window_3": _round_mapping(
            window[VITAL_COLUMNS].tail(min(3, len(window))).mean(numeric_only=True).to_dict()
        ),
        "window_5": _round_mapping(
            window[VITAL_COLUMNS].tail(min(5, len(window))).mean(numeric_only=True).to_dict()
        ),
    }

    baseline_deviation = {
        column: round(float(latest[column]) - float(baseline_latest[column]), 2)
        for column in VITAL_COLUMNS
    }

    flags = detect_threshold_flags(latest)
    patterns = detect_patterns(window)
    severity = _score_to_severity(
        float(latest["news2"]), float(latest["shock_index"]), float(latest["map"])
    )
    if any(item["severity"] == "CRITICAL" for item in flags + patterns):
        severity = "CRITICAL"
    elif any(item["severity"] == "WARNING" for item in flags + patterns):
        severity = "WARNING"

    return {
        "cursor_minute": int(latest["minute"]),
        "window_start_minute": int(window["minute"].iloc[0]),
        "window_end_minute": int(window["minute"].iloc[-1]),
        "latest_reading": {
            "minute": int(latest["minute"]),
            "hr": int(latest["hr"]),
            "spo2": int(latest["spo2"]),
            "sbp": int(latest["sbp"]),
            "dbp": int(latest["dbp"]),
            "temp_c": round(float(latest["temp_c"]), 1),
            "rr": int(latest["rr"]),
            "etco2": int(latest["etco2"]),
        },
        "derived_metrics": {
            "news2": int(latest["news2"]),
            "shock_index": float(latest["shock_index"]),
            "map": float(latest["map"]),
            "qsofa_limited": int(latest["qsofa_limited"]),
        },
        "rolling_means": rolling_means,
        "slopes_per_minute": _round_mapping(slopes),
        "baseline_deviation": baseline_deviation,
        "threshold_flags": flags,
        "detected_patterns": patterns,
        "severity_hint": severity,
    }
