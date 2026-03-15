from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from google.adk.tools.tool_context import ToolContext

from tools.analytics import summarize_window
from tools.vitaldb_adapter import normalize_vitaldb_csv_with_metadata


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = ROOT / "data" / "scenarios"
NORMALIZED_DIR = ROOT / "data" / "normalized"


def _state_key(name: str) -> str:
    return f"monitor.{name}"


def _recovery_response(code: str, message: str, **extra: Any) -> dict[str, Any]:
    payload = {"status": "recovery", "recovery_code": code, "message": message}
    payload.update(extra)
    return payload


def _ok_response(**payload: Any) -> dict[str, Any]:
    return {"status": "ok", **payload}


def _scenario_path(name: str) -> Path:
    return SCENARIO_DIR / f"{name}.csv"


def _active_dataset_path(tool_context: ToolContext) -> tuple[Path | None, dict[str, Any] | None]:
    dataset_path = tool_context.state.get(_state_key("dataset_path"))
    if not dataset_path:
        return None, _recovery_response(
            "no_active_dataset",
            "No patient data source is active. Load a built-in scenario or a VitalDB CSV first.",
            available_scenarios=list_scenarios(),
        )

    path = Path(str(dataset_path))
    if not path.exists():
        return None, _recovery_response(
            "dataset_path_missing",
            f"The active dataset path no longer exists: {path}",
            dataset_path=str(path),
        )
    return path, None


def _read_active_dataframe(tool_context: ToolContext) -> tuple[pd.DataFrame | None, dict[str, Any] | None]:
    path, error = _active_dataset_path(tool_context)
    if error:
        return None, error

    df = pd.read_csv(path)
    if df.empty:
        return None, _recovery_response(
            "empty_dataset",
            f"The active dataset at {path} contains no rows.",
            dataset_path=str(path),
        )
    return df, None


def list_scenarios() -> list[str]:
    """Return the available patient-monitor demo scenarios."""
    return sorted(path.stem for path in SCENARIO_DIR.glob("*.csv"))


def load_vitaldb_csv(path: str, tool_context: ToolContext) -> dict[str, Any]:
    """
    Normalize a VitalDB-style CSV into VitalGuard monitor columns and load it for playback.

    Accepted tracks:
    - Solar8000/HR
    - Solar8000/PLETH_SPO2
    - Solar8000/NIBP_SBP
    - Solar8000/NIBP_DBP
    - Solar8000/RR
    - Solar8000/BT
    - Solar8000/ETCO2

    Degraded mode:
    - Missing optional temperature or EtCO2 is allowed and will be imputed.
    - Sparse gaps in present signals are interpolated and reported.
    - Entirely missing required tracks return a structured recovery response instead of throwing.
    """
    source_path = Path(path).expanduser()
    if not source_path.is_absolute():
        source_path = (ROOT / source_path).resolve()
    if not source_path.exists():
        return _recovery_response(
            "vitaldb_file_missing",
            f"VitalDB CSV not found: {source_path}",
            required_path_format=r"C:\full\path\to\case.csv",
            supplied_path=path,
        )

    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = NORMALIZED_DIR / f"{source_path.stem}_normalized.csv"
    normalized, metadata = normalize_vitaldb_csv_with_metadata(source_path, output_path=output_path)

    if not metadata["can_analyze"]:
        return _recovery_response(
            "vitaldb_missing_required_tracks",
            "VitalDB file is missing required bedside-monitor tracks.",
            source_path=str(source_path),
            found_tracks=metadata["found_tracks"],
            missing_required_signals=metadata["missing_required_signals"],
            accepted_track_names=metadata["accepted_track_names"],
            degraded_mode_possible=bool(metadata["imputed_optional_signals"] or metadata["interpolated_signals"]),
        )

    tool_context.state[_state_key("active_scenario")] = source_path.stem
    tool_context.state[_state_key("dataset_path")] = str(output_path)
    tool_context.state[_state_key("dataset_source")] = "vitaldb"
    tool_context.state[_state_key("dataset_profile")] = metadata
    tool_context.state[_state_key("cursor")] = -1
    tool_context.state[_state_key("window_minutes")] = 10
    tool_context.state[_state_key("complete")] = False

    return _ok_response(
        dataset_source="vitaldb",
        source_path=str(source_path),
        normalized_path=str(output_path),
        total_minutes=int(len(normalized)),
        degraded_mode=metadata["degraded_mode"],
        degradation_reasons=metadata["degradation_reasons"],
        found_tracks=metadata["found_tracks"],
        message=f"Normalized {source_path.name} and loaded it for playback.",
    )


def load_scenario(name: str, tool_context: ToolContext) -> dict[str, Any]:
    """Load a scenario into the monitoring session and reset playback to minute 0."""
    path = _scenario_path(name)
    if not path.exists():
        return _recovery_response(
            "unknown_scenario",
            f"Unknown scenario '{name}'.",
            available_scenarios=list_scenarios(),
        )

    df = pd.read_csv(path)
    tool_context.state[_state_key("active_scenario")] = name
    tool_context.state[_state_key("dataset_path")] = str(path)
    tool_context.state[_state_key("dataset_source")] = "scenario"
    tool_context.state[_state_key("dataset_profile")] = {
        "degraded_mode": False,
        "degradation_reasons": [],
        "found_tracks": {signal: signal for signal in ["hr", "spo2", "sbp", "dbp", "temp_c", "rr", "etco2"]},
    }
    tool_context.state[_state_key("cursor")] = -1
    tool_context.state[_state_key("window_minutes")] = 10
    tool_context.state[_state_key("complete")] = False

    return _ok_response(
        scenario_name=name,
        total_minutes=int(df["minute"].max()) + 1,
        message=f"Loaded {name} and reset playback to minute 0.",
    )


def set_monitor_minute(minute: int, tool_context: ToolContext) -> dict[str, Any]:
    """Jump the monitoring cursor to a specific minute for scripted demos."""
    scenario_name = str(tool_context.state.get(_state_key("active_scenario"), ""))
    if not scenario_name:
        return _recovery_response(
            "no_active_dataset",
            "No patient data source is active. Load a scenario or VitalDB CSV first.",
            available_scenarios=list_scenarios(),
        )

    df, error = _read_active_dataframe(tool_context)
    if error:
        return error

    assert df is not None
    requested_minute = int(minute)
    bounded_minute = max(0, min(requested_minute, len(df) - 1))
    tool_context.state[_state_key("cursor")] = bounded_minute
    tool_context.state[_state_key("complete")] = bounded_minute >= len(df) - 1

    response = _ok_response(
        scenario_name=scenario_name,
        cursor_minute=bounded_minute,
        requested_minute=requested_minute,
        valid_minute_range=[0, len(df) - 1],
        message=f"Monitoring cursor set to minute {bounded_minute}.",
    )
    if bounded_minute != requested_minute:
        response["recovery_note"] = (
            f"Requested minute {requested_minute} was out of range and was clamped to {bounded_minute}."
        )
    return response


def get_latest_data(
    window_minutes: int = 10,
    advance_minutes: int = 5,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Return the latest scenario window and advance the playback cursor."""
    if tool_context is None:
        return _recovery_response("missing_tool_context", "Tool context is required.")

    scenario_name = str(tool_context.state.get(_state_key("active_scenario"), ""))
    if not scenario_name:
        return _recovery_response(
            "no_active_dataset",
            "No patient data source is active. Load a scenario or VitalDB CSV first.",
            available_scenarios=list_scenarios(),
        )

    df, error = _read_active_dataframe(tool_context)
    if error:
        return error

    assert df is not None
    current_cursor = int(tool_context.state.get(_state_key("cursor"), -1))
    bounded_window = max(1, int(window_minutes))
    bounded_advance = max(1, int(advance_minutes))

    if current_cursor < 0:
        new_cursor = min(bounded_window - 1, len(df) - 1)
    else:
        new_cursor = min(current_cursor + bounded_advance, len(df) - 1)

    tool_context.state[_state_key("cursor")] = new_cursor
    tool_context.state[_state_key("window_minutes")] = bounded_window
    tool_context.state[_state_key("complete")] = new_cursor >= len(df) - 1

    start_index = max(0, new_cursor - bounded_window + 1)
    window = df.iloc[start_index : new_cursor + 1].reset_index(drop=True)

    if len(window) < 2:
        return _recovery_response(
            "short_window",
            "The current data window is too short for trend analysis. Advance the stream or request a later minute.",
            cursor_minute=new_cursor,
            rows_available=len(window),
        )

    return _ok_response(
        scenario_name=scenario_name,
        window_start_minute=int(window["minute"].iloc[0]),
        window_end_minute=int(window["minute"].iloc[-1]),
        cursor_minute=new_cursor,
        is_complete=bool(tool_context.state[_state_key("complete")]),
        rows=window.to_dict(orient="records"),
    )


def get_parameter_summary(tool_context: ToolContext) -> dict[str, Any]:
    """Return the latest raw values and derived metrics for the active cursor."""
    scenario_name = str(tool_context.state.get(_state_key("active_scenario"), ""))
    if not scenario_name:
        return _recovery_response(
            "no_active_dataset",
            "No patient data source is active. Load a scenario or VitalDB CSV first.",
            available_scenarios=list_scenarios(),
        )

    df, error = _read_active_dataframe(tool_context)
    if error:
        return error

    assert df is not None
    current_cursor = int(tool_context.state.get(_state_key("cursor"), 0))
    window_minutes = int(tool_context.state.get(_state_key("window_minutes"), 10))
    current_cursor = max(0, min(current_cursor, len(df) - 1))

    summary = summarize_window(df, current_cursor, window_minutes=window_minutes)
    summary["status"] = "ok"
    summary["scenario_name"] = scenario_name
    summary["dataset_source"] = tool_context.state.get(_state_key("dataset_source"), "scenario")
    summary["dataset_profile"] = tool_context.state.get(_state_key("dataset_profile"), {})
    summary["is_complete"] = bool(tool_context.state.get(_state_key("complete"), False))
    return summary


def analyze_current_window(tool_context: ToolContext) -> dict[str, Any]:
    """Compute derived metrics, slopes, threshold flags, and multi-parameter patterns."""
    scenario_name = str(tool_context.state.get(_state_key("active_scenario"), ""))
    if not scenario_name:
        return _recovery_response(
            "no_active_dataset",
            "No patient data source is active. Load a scenario or VitalDB CSV first.",
            available_scenarios=list_scenarios(),
        )

    df, error = _read_active_dataframe(tool_context)
    if error:
        return error

    assert df is not None
    current_cursor = int(tool_context.state.get(_state_key("cursor"), 0))
    window_minutes = int(tool_context.state.get(_state_key("window_minutes"), 10))
    current_cursor = max(0, min(current_cursor, len(df) - 1))

    if current_cursor < 1:
        return _recovery_response(
            "short_window",
            "At least two time steps are required before a trend assessment is meaningful.",
            cursor_minute=current_cursor,
            suggestion="Advance the stream or jump to a later minute.",
        )

    summary = summarize_window(df, current_cursor, window_minutes=window_minutes)
    summary["status"] = "ok"
    summary["scenario_name"] = scenario_name
    summary["dataset_source"] = tool_context.state.get(_state_key("dataset_source"), "scenario")
    summary["dataset_profile"] = tool_context.state.get(_state_key("dataset_profile"), {})
    summary["analysis_note"] = (
        "qSOFA is limited to RR and SBP because altered mental status is not available in the simulated monitor feed."
    )
    return summary
