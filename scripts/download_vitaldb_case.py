from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import vitaldb


DEFAULT_TRACKS = [
    "Solar8000/HR",
    "Solar8000/PLETH_SPO2",
    "Solar8000/NIBP_SBP",
    "Solar8000/NIBP_DBP",
    "Solar8000/RR",
    "Solar8000/BT",
    "Solar8000/ETCO2",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download a real VitalDB case as a CSV with the bedside monitor tracks used by VitalGuard."
    )
    parser.add_argument("--caseid", type=int, default=4096, help="VitalDB case ID to download.")
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Sampling interval in seconds. 60 gives one row per minute.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data") / "vitaldb_case_4096.csv",
        help="Output CSV path.",
    )
    args = parser.parse_args()

    values = vitaldb.load_case(args.caseid, DEFAULT_TRACKS, interval=args.interval)
    df = pd.DataFrame(values, columns=DEFAULT_TRACKS)
    df.insert(0, "Time", pd.date_range("2024-01-01", periods=len(df), freq=f"{args.interval}s"))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)

    print(f"Saved case {args.caseid} to {args.output} ({len(df)} rows)")
    print("Tracks:")
    for track in DEFAULT_TRACKS:
        print(f"- {track}")


if __name__ == "__main__":
    main()
