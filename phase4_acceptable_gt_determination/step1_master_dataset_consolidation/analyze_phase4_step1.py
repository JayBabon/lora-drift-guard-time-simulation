#!/usr/bin/env python3
import glob
import os
from datetime import datetime

import pandas as pd


def latest_step5_dir(ns3_dir: str) -> str:
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase3_step5_*")
    dirs = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    dirs = sorted(dirs, key=os.path.getmtime, reverse=True)
    if not dirs:
        raise FileNotFoundError(f"No Phase 3 Step 5 directory found at: {pattern}")
    return dirs[0]


def latest_step6_dir(ns3_dir: str) -> str:
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase3_step6_*")
    dirs = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    dirs = sorted(dirs, key=os.path.getmtime, reverse=True)
    if not dirs:
        raise FileNotFoundError(f"No Phase 3 Step 6 directory found at: {pattern}")
    return dirs[0]


def main():
    ns3_dir = os.path.expanduser("~/ns-3-dev")

    step5_dir = latest_step5_dir(ns3_dir)
    step6_dir = latest_step6_dir(ns3_dir)

    summary_csv = os.path.join(step5_dir, "phase3_step5_summary_by_drift_gt.csv")
    min_gt_csv = os.path.join(step5_dir, "phase3_step5_min_gt_per_drift.csv")
    costing_csv = os.path.join(step6_dir, "phase3_step6_threshold_costing.csv")

    for p in [summary_csv, min_gt_csv, costing_csv]:
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Required file not found: {p}")

    summary_df = pd.read_csv(summary_csv)
    min_df = pd.read_csv(min_gt_csv)
    costing_df = pd.read_csv(costing_csv)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(ns3_dir, f"contrib/lora_drift_gt/results/phase4_step1_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    master_df = summary_df.merge(
        min_df[["scenario_id", "pdr_target_percent", "min_gtMs"]],
        on="scenario_id",
        how="left",
    )

    master_df = master_df.merge(
        costing_df[["scenario_id", "gtMs", "meets_target", "avoidable_gt_overhead_ms"]],
        on=["scenario_id", "gtMs"],
        how="left",
    )

    master_df = master_df.sort_values(["srcPpm", "gtMs", "scenario_id"]).reset_index(drop=True)

    master_csv = os.path.join(outdir, "phase4_step1_master_drift_gt_dataset.csv")
    master_df.to_csv(master_csv, index=False)

    compact_cols = [
        "scenario_id", "srcPpm", "relayPpm", "sinkPpm", "gtModel", "gtMs", "k_runs",
        "pdr_target_percent", "min_gtMs", "meets_target", "avoidable_gt_overhead_ms",
        "pdr_ok_percent_mean", "plr_percent_mean", "total_viol_mean",
        "violation_rate_mean", "avg_delay_ok_ms_mean",
    ]
    compact_df = master_df[[c for c in compact_cols if c in master_df.columns]].copy()
    compact_csv = os.path.join(outdir, "phase4_step1_master_compact.csv")
    compact_df.to_csv(compact_csv, index=False)

    report_txt = os.path.join(outdir, "phase4_step1_report.txt")
    with open(report_txt, "w", encoding="utf-8") as f:
        f.write("PHASE 4 STEP 1 - MASTER DRIFT x GT DATASET REPORT\n")
        f.write("=================================================\n\n")
        f.write(f"Input summary: {summary_csv}\n")
        f.write(f"Input min GT map: {min_gt_csv}\n")
        f.write(f"Input costing table: {costing_csv}\n")
        f.write(f"Output folder: {outdir}\n\n")
        f.write("Outputs:\n")
        f.write(f"- {master_csv}\n")
        f.write(f"- {compact_csv}\n")
        f.write(f"- {report_txt}\n\n")
        f.write("Purpose:\n")
        f.write("- Consolidate drift x GT summary results\n")
        f.write("- Attach threshold-related fields\n")
        f.write("- Prepare the master input table for acceptable-GT determination\n")

    print("DONE Phase 4 Step 1")
    print("Outdir:", outdir)
    print("Saved:")
    print(" -", master_csv)
    print(" -", compact_csv)
    print(" -", report_txt)


if __name__ == "__main__":
    main()
