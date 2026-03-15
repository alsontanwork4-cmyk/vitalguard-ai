from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "scenarios"


def piecewise(points: dict[int, float], total_minutes: int = 60) -> list[float]:
    anchors = sorted(points.items())
    values: list[float] = [0.0] * total_minutes

    for index, (minute, value) in enumerate(anchors[:-1]):
        next_minute, next_value = anchors[index + 1]
        span = max(1, next_minute - minute)
        for current in range(minute, next_minute):
            progress = (current - minute) / span
            values[current] = value + (next_value - value) * progress

    last_minute, last_value = anchors[-1]
    for current in range(last_minute, total_minutes):
        values[current] = last_value

    return values


def build_dataframe(config: dict[str, dict[int, float]]) -> pd.DataFrame:
    minute = list(range(60))
    df = pd.DataFrame({"minute": minute})

    for column, anchors in config.items():
        series = piecewise(anchors, total_minutes=len(minute))
        if column == "temp_c":
            df[column] = [round(value, 1) for value in series]
        else:
            df[column] = [round(value) for value in series]

    return df


def stable_series(base: float, amplitude: float, period: float, temp: bool = False) -> list[float]:
    values = []
    for minute in range(60):
        value = base + math.sin(minute / period) * amplitude + math.cos(minute / (period * 1.7)) * amplitude * 0.5
        values.append(round(value, 1) if temp else round(value))
    return values


def scenario_definitions() -> dict[str, pd.DataFrame]:
    sepsis = build_dataframe(
        {
            "hr": {0: 75, 15: 78, 25: 100, 40: 110, 50: 125, 59: 128},
            "spo2": {0: 96, 25: 95, 40: 94, 50: 92, 59: 90},
            "sbp": {0: 125, 25: 118, 40: 105, 50: 85, 59: 82},
            "dbp": {0: 78, 25: 74, 40: 68, 50: 55, 59: 52},
            "temp_c": {0: 37.0, 15: 37.2, 25: 38.5, 40: 39.0, 50: 39.5, 59: 39.7},
            "rr": {0: 16, 15: 18, 25: 24, 40: 28, 50: 32, 59: 34},
            "etco2": {0: 38, 25: 37, 40: 35, 50: 33, 59: 31},
        }
    )

    bleeding = build_dataframe(
        {
            "hr": {0: 75, 20: 78, 30: 90, 45: 100, 55: 118, 59: 125},
            "spo2": {0: 97, 30: 97, 45: 96, 59: 95},
            "sbp": {0: 125, 20: 122, 30: 118, 45: 112, 55: 88, 59: 80},
            "dbp": {0: 78, 20: 76, 30: 74, 45: 70, 55: 58, 59: 50},
            "temp_c": {0: 36.9, 59: 37.1},
            "rr": {0: 15, 30: 18, 45: 20, 55: 24, 59: 26},
            "etco2": {0: 38, 30: 37, 45: 35, 59: 32},
        }
    )

    respiratory = build_dataframe(
        {
            "hr": {0: 82, 20: 85, 30: 92, 50: 104, 59: 112},
            "spo2": {0: 97, 20: 96, 30: 94, 45: 92, 55: 89, 59: 88},
            "sbp": {0: 128, 30: 122, 50: 116, 59: 110},
            "dbp": {0: 80, 30: 78, 50: 74, 59: 72},
            "temp_c": {0: 37.4, 30: 37.9, 50: 38.2, 59: 38.3},
            "rr": {0: 16, 20: 18, 30: 22, 50: 24, 59: 28},
            "etco2": {0: 37, 30: 35, 50: 33, 59: 31},
        }
    )

    stable = pd.DataFrame(
        {
            "minute": list(range(60)),
            "hr": stable_series(76, 3.0, 5.0),
            "spo2": stable_series(97, 1.0, 7.0),
            "sbp": stable_series(122, 4.0, 6.5),
            "dbp": stable_series(78, 2.0, 6.0),
            "temp_c": stable_series(36.9, 0.2, 8.5, temp=True),
            "rr": stable_series(16, 1.2, 7.5),
            "etco2": stable_series(37, 1.0, 6.8),
        }
    )

    return {
        "sepsis_onset": sepsis,
        "compensatory_shock": bleeding,
        "respiratory_deterioration": respiratory,
        "stable_postop": stable,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in scenario_definitions().items():
        df.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)
        print(f"wrote {name}.csv ({len(df)} rows)")


if __name__ == "__main__":
    main()
