from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Iterable

import pandas as pd


TARGET_COLUMNS = ["minute", "hr", "spo2", "sbp", "dbp", "temp_c", "rr", "etco2"]
OPTIONAL_SIGNALS = {"temp_c": 37.0, "etco2": 35.0}
VITALDB_ALIASES = {
    "hr": ["Solar8000/HR", "Solar8000/PLETH_HR", "HR", "hr"],
    "spo2": ["Solar8000/SPO2", "Solar8000/PLETH_SPO2", "SpO2", "spo2", "SPO2"],
    "sbp": ["Solar8000/NIBP_SBP", "Solar8000/ART_SBP", "Solar8000/FEM_SBP", "SBP", "sbp"],
    "dbp": ["Solar8000/NIBP_DBP", "Solar8000/ART_DBP", "Solar8000/FEM_DBP", "DBP", "dbp"],
    "temp_c": ["Solar8000/BT", "Temp", "temp_c", "TEMP"],
    "rr": ["Solar8000/RR_CO2", "Solar8000/RR", "RR", "rr"],
    "etco2": ["Solar8000/ETCO2", "EtCO2", "ETCO2", "etco2"],
}
TIME_ALIASES = ["time", "Time", "dt", "timestamp", "Timestamp"]


def _choose_column(df: pd.DataFrame, aliases: Iterable[str]) -> str | None:
    for alias in aliases:
        if alias in df.columns:
            return alias
    return None


def _coerce_numeric(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.interpolate(limit_direction="both").ffill().bfill()


def normalize_vitaldb_csv_with_metadata(
    source_path: str | Path,
    output_path: str | Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Normalize a VitalDB export into VitalGuard monitor columns and return recovery metadata.

    Recovery policy:
    - Entirely missing required bedside-monitor tracks block analysis.
    - Missing optional signals (`temp_c`, `etco2`) are imputed with safe defaults and flagged.
    - Sparse NaNs inside a present track are interpolated and flagged as degraded mode.
    """
    source = Path(source_path)
    df = pd.read_csv(source)
    normalized = pd.DataFrame()
    metadata: dict[str, Any] = {
        "source_path": str(source),
        "accepted_track_names": VITALDB_ALIASES,
        "found_tracks": {},
        "missing_required_signals": [],
        "imputed_optional_signals": [],
        "interpolated_signals": [],
        "degraded_mode": False,
        "degradation_reasons": [],
    }

    time_column = _choose_column(df, TIME_ALIASES)
    if time_column:
        timestamps = pd.to_datetime(df[time_column], errors="coerce")
        if timestamps.notna().sum() >= 2:
            seconds = (timestamps - timestamps.iloc[0]).dt.total_seconds().fillna(0)
            normalized["minute"] = (seconds / 60).round().astype(int)
        else:
            normalized["minute"] = range(len(df))
            metadata["degraded_mode"] = True
            metadata["degradation_reasons"].append(
                f"Time column '{time_column}' could not be parsed reliably; row order was used as minutes."
            )
    else:
        normalized["minute"] = range(len(df))
        metadata["degraded_mode"] = True
        metadata["degradation_reasons"].append(
            "No recognized time column was found; row order was used as minutes."
        )

    for target, aliases in VITALDB_ALIASES.items():
        column = _choose_column(df, aliases)
        if column is None:
            if target in OPTIONAL_SIGNALS:
                normalized[target] = OPTIONAL_SIGNALS[target]
                metadata["imputed_optional_signals"].append(target)
                metadata["degraded_mode"] = True
                metadata["degradation_reasons"].append(
                    f"Optional signal '{target}' was absent and was imputed with a safe default."
                )
                continue
            metadata["missing_required_signals"].append(target)
            continue

        numeric = pd.to_numeric(df[column], errors="coerce")
        metadata["found_tracks"][target] = column

        if numeric.notna().sum() == 0:
            if target in OPTIONAL_SIGNALS:
                normalized[target] = OPTIONAL_SIGNALS[target]
                metadata["imputed_optional_signals"].append(target)
                metadata["degraded_mode"] = True
                metadata["degradation_reasons"].append(
                    f"Optional signal '{target}' was present as '{column}' but contained no usable numeric values."
                )
            else:
                metadata["missing_required_signals"].append(target)
            continue

        if numeric.isna().any():
            metadata["interpolated_signals"].append(target)
            metadata["degraded_mode"] = True
            metadata["degradation_reasons"].append(
                f"Signal '{target}' contained sparse gaps and was linearly interpolated."
            )

        normalized[target] = _coerce_numeric(numeric)

    metadata["can_analyze"] = not metadata["missing_required_signals"]
    metadata["missing_optional_signals"] = [
        signal for signal in OPTIONAL_SIGNALS if signal in metadata["imputed_optional_signals"]
    ]

    if metadata["can_analyze"]:
        normalized = (
            normalized.groupby("minute", as_index=False)
            .mean(numeric_only=True)
            .sort_values("minute")
            .reset_index(drop=True)
        )
        normalized["minute"] = range(len(normalized))

        for column in ["hr", "spo2", "sbp", "dbp", "rr", "etco2"]:
            normalized[column] = normalized[column].round().astype(int)
        normalized["temp_c"] = normalized["temp_c"].round(1)
        normalized = normalized[TARGET_COLUMNS]

        if output_path is not None:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            normalized.to_csv(output_path, index=False)

    return normalized, metadata


def normalize_vitaldb_csv(source_path: str | Path, output_path: str | Path | None = None) -> pd.DataFrame:
    """
    Backwards-compatible wrapper that raises when required monitor tracks are missing.
    """
    normalized, metadata = normalize_vitaldb_csv_with_metadata(source_path, output_path=output_path)
    if not metadata["can_analyze"]:
        missing = ", ".join(metadata["missing_required_signals"])
        raise ValueError(
            "Could not find required VitalDB signals: "
            f"{missing}. Accepted track names: {VITALDB_ALIASES}"
        )
    return normalized
