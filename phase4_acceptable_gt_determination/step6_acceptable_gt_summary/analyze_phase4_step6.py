#!/usr/bin/env python3
import glob
import os
from datetime import datetime

import pandas as pd


def latest_step4_dir(ns3_dir: str) -> str:
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase4_step4_*")
    dirs = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    dirs = sorted(dirs, key=os.path.getmtime, reverse=True)
    if not dirs:
        raise FileNotFoundError(f"No Phase 4 Step 4 directory found at: {pattern}")
    return dirs[0]


def latest_step5_dir(ns3_dir: str) -> str:
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase4_step5_*")
    dirs = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    dirs = sorted(dirs, key=os.path.getmtime, reverse=True)
    if not dirs:
        raise FileNotFoundError(f"No Phase 4 Step 5 directory found at: {pattern}")
    return dirs[0]


def main():
    ns3_dir = os.path.expanduser("~/ns-3-dev")
    step4_dir = latest_step4_dir(ns3_dir)
    step5_dir = latest_step5_dir(ns3_dir)

    opt_csv = os.path.join(step4_dir, "phase4_step4_threshold_optimization.csv")
    region_csv = os.path.join(step5_dir, "phase4_step5_region_optimization.csv")

    for p in [opt_csv, region_csv]:
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Required file not found: {p}")

    opt_df = pd.read_csv(opt_csv)
    region_df = pd.read_csv(region_csv)

    merged = opt_df.merge(
        region_df[[
            "scenario_id", "stable_region_exists", "stable_gt_start_ms",
            "stable_gt_end_ms", "stable_region_width_ms", "robust_region_label",
        ]],
        on="scenario_id",
        how="left",
    )
    merged = merged.sort_values(["srcPpm", "scenario_id"]).reset_index(drop=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(ns3_dir, f"contrib/lora_drift_gt/results/phase4_step6_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    summary_path = os.path.join(outdir, "phase4_step6_acceptable_gt_summary.csv")
    merged.to_csv(summary_path, index=False)

    compact_cols = [
        "scenario_id", "srcPpm", "relayPpm", "sinkPpm", "selected_gtMs", "selection_status",
        "stable_region_exists", "stable_gt_start_ms", "stable_gt_end_ms",
        "stable_region_width_ms", "robust_region_label",
    ]
    compact_df = merged[[c for c in compact_cols if c in merged.columns]].copy()
    compact_path = os.path.join(outdir, "phase4_step6_acceptable_gt_compact.csv")
    compact_df.to_csv(compact_path, index=False)

    matrix_df = compact_df[["scenario_id", "selected_gtMs", "robust_region_label"]].copy()
    matrix_path = os.path.join(outdir, "phase4_step6_acceptable_gt_matrix.csv")
    matrix_df.to_csv(matrix_path, index=False)

    report_path = os.path.join(outdir, "phase4_step6_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("PHASE 4 STEP 6 - ACCEPTABLE GT SUMMARY REPORT\n")
        f.write("=============================================\n\n")
        f.write(f"Input threshold optimization: {opt_csv}\n")
        f.write(f"Input region optimization: {region_csv}\n")
        f.write(f"Output folder: {outdir}\n\n")
        f.write("Outputs:\n")
        f.write(f"- {summary_path}\n")
        f.write(f"- {compact_path}\n")
        f.write(f"- {matrix_path}\n")
        f.write(f"- {report_path}\n\n")
        f.write("Purpose:\n")
        f.write("- Produce the final acceptable-GT outputs per drift level\n")
        f.write("- Combine minimum acceptable GT with robust operating-region context\n")
        f.write("- Prepare Objective 4 outputs for strategy formulation in Phase 5\n")

    print("DONE Phase 4 Step 6")
    print("Outdir:", outdir)
    print("Saved:")
    print(" -", summary_path)
    print(" -", compact_path)
    print(" -", matrix_path)
    print(" -", report_path)


if __name__ == "__main__":
    main()
