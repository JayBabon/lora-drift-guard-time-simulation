#!/usr/bin/env python3
import argparse
import glob
import math
import os
from datetime import datetime

import pandas as pd


def latest_raw_csv(ns3_dir: str) -> str:
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase2_step5_raw_*.csv")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No Phase 2 Step 5 raw CSV found at: {pattern}")
    return files[0]


def ci95_halfwidth(series: pd.Series) -> float:
    s = pd.to_numeric(series, errors="coerce").dropna()
    n = len(s)
    if n <= 1:
        return 0.0
    return 1.96 * (s.std(ddof=1) / math.sqrt(n))


def main():
    parser = argparse.ArgumentParser(description="Aggregate Phase 2 drift-impact raw CSV into scenario-level summaries.")
    parser.add_argument("--input", default="", help="Path to phase2_step5_raw_*.csv. Leave blank to auto-pick latest.")
    parser.add_argument("--outdir", default="", help="Output directory. Leave blank to auto-create timestamped folder.")
    args = parser.parse_args()

    ns3_dir = os.path.expanduser("~/ns-3-dev")
    inp = args.input.strip() or latest_raw_csv(ns3_dir)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = args.outdir.strip() or os.path.join(ns3_dir, f"contrib/lora_drift_gt/results/phase2_step6_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    df = pd.read_csv(inp)

    num_cols = [
        "seed", "run", "srcPpm", "relayPpm", "sinkPpm",
        "tx_total", "relay_rx_total", "relay_rx_ok", "relay_viol",
        "relay_fwd_total", "sink_rx_total", "sink_rx_ok", "sink_viol",
        "pdr_ok_percent", "plr_percent", "avg_delay_ok_ms",
        "avg_gt_used_ok_ms", "total_viol", "violation_rate"
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    required_cols = ["scenario_id", "srcPpm", "relayPpm", "sinkPpm", "gtModel", "run"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in input CSV: {missing}")

    group_cols = ["scenario_id", "srcPpm", "relayPpm", "sinkPpm", "gtModel"]
    metrics = [
        "pdr_ok_percent",
        "plr_percent",
        "total_viol",
        "violation_rate",
        "avg_delay_ok_ms",
    ]

    summary_rows = []
    for keys, sub in df.groupby(group_cols, dropna=False):
        row = {
            "scenario_id": keys[0],
            "srcPpm": keys[1],
            "relayPpm": keys[2],
            "sinkPpm": keys[3],
            "gtModel": keys[4],
            "k_runs": int(sub["run"].count()),
        }

        for metric in metrics:
            if metric not in sub.columns:
                row[f"{metric}_mean"] = 0.0
                row[f"{metric}_std"] = 0.0
                row[f"{metric}_median"] = 0.0
                row[f"{metric}_ci95_halfwidth"] = 0.0
                continue

            series = pd.to_numeric(sub[metric], errors="coerce")
            clean = series.dropna()
            row[f"{metric}_mean"] = float(clean.mean()) if len(clean) else 0.0
            row[f"{metric}_std"] = float(clean.std(ddof=1)) if len(clean) > 1 else 0.0
            row[f"{metric}_median"] = float(clean.median()) if len(clean) else 0.0
            row[f"{metric}_ci95_halfwidth"] = float(ci95_halfwidth(clean))

        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows).sort_values(["srcPpm", "scenario_id"])

    detailed_path = os.path.join(outdir, "phase2_step6_summary_by_scenario.csv")
    summary_df.to_csv(detailed_path, index=False)

    compact_cols = [
        "scenario_id", "srcPpm", "relayPpm", "sinkPpm", "gtModel", "k_runs",
        "pdr_ok_percent_mean", "pdr_ok_percent_std", "pdr_ok_percent_ci95_halfwidth",
        "plr_percent_mean", "plr_percent_std",
        "total_viol_mean", "total_viol_std",
        "violation_rate_mean", "violation_rate_std",
        "avg_delay_ok_ms_mean", "avg_delay_ok_ms_std",
    ]
    compact_df = summary_df[[col for col in compact_cols if col in summary_df.columns]].copy()
    compact_path = os.path.join(outdir, "phase2_step6_compact_summary.csv")
    compact_df.to_csv(compact_path, index=False)

    report_path = os.path.join(outdir, "phase2_step6_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"INPUT: {inp}\n")
        f.write(f"OUTDIR: {outdir}\n\n")
        f.write("Outputs:\n")
        f.write(f"- {detailed_path}\n")
        f.write(f"- {compact_path}\n")
        f.write(f"- {report_path}\n\n")
        f.write("Aggregation method:\n")
        f.write("- Statistical summary aggregation\n")
        f.write("- Scenario-based aggregation\n")
        f.write("- Metrics summarized: PDR, PLR, total violations, violation rate, average delay\n")

    evid_dir = os.path.join(ns3_dir, "contrib/lora_drift_gt/evidence/phase2_step6")
    os.makedirs(evid_dir, exist_ok=True)
    proof_path = os.path.join(evid_dir, "RUN_PROOF.txt")
    with open(proof_path, "w", encoding="utf-8") as f:
        f.write("PHASE 2 STEP 6 - AGGREGATION PROOF\n")
        f.write("==================================\n")
        f.write(f"Input: {inp}\n")
        f.write(f"Output directory: {outdir}\n")
        f.write(f"Detailed summary: {detailed_path}\n")
        f.write(f"Compact summary: {compact_path}\n")
        f.write(f"Report: {report_path}\n\n")
        f.write("Compact summary preview:\n")
        f.write(compact_df.head(10).to_csv(index=False))

    print("DONE Phase 2 Step 6")
    print("Input:", inp)
    print("Outdir:", outdir)
    print("Saved:")
    print(" -", detailed_path)
    print(" -", compact_path)
    print(" -", report_path)
    print("Proof:", proof_path)


if __name__ == "__main__":
    main()
