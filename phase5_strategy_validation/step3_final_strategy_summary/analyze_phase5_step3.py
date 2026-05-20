#!/usr/bin/env python3
import glob
import os
from datetime import datetime

import pandas as pd


def latest_step1_dir(ns3_dir: str) -> str:
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase5_step1_*")
    dirs = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    dirs = sorted(dirs, key=os.path.getmtime, reverse=True)
    if not dirs:
        raise FileNotFoundError(f"No Phase 5 Step 1 directory found at: {pattern}")
    return dirs[0]


def latest_step2_dir(ns3_dir: str) -> str:
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase5_step2_*")
    dirs = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    dirs = sorted(dirs, key=os.path.getmtime, reverse=True)
    if not dirs:
        raise FileNotFoundError(f"No Phase 5 Step 2 directory found at: {pattern}")
    return dirs[0]


def latest_phase4_step6_dir(ns3_dir: str) -> str:
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase4_step6_*")
    dirs = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    dirs = sorted(dirs, key=os.path.getmtime, reverse=True)
    if not dirs:
        raise FileNotFoundError(f"No Phase 4 Step 6 directory found at: {pattern}")
    return dirs[0]


def main():
    ns3_dir = os.path.expanduser("~/ns-3-dev")

    step1_dir = latest_step1_dir(ns3_dir)
    step2_dir = latest_step2_dir(ns3_dir)
    step4_6_dir = latest_phase4_step6_dir(ns3_dir)

    rules_csv = os.path.join(step1_dir, "phase5_step1_strategy_rules.csv")
    map_csv = os.path.join(step1_dir, "phase5_step1_threshold_strategy_map.csv")
    validation_csv = os.path.join(step2_dir, "phase5_step2_validation_table.csv")
    acceptable_csv = os.path.join(step4_6_dir, "phase4_step6_acceptable_gt_summary.csv")

    for p in [rules_csv, map_csv, validation_csv, acceptable_csv]:
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Required file not found: {p}")

    rules_df = pd.read_csv(rules_csv)
    map_df = pd.read_csv(map_csv)
    val_df = pd.read_csv(validation_csv)
    acc_df = pd.read_csv(acceptable_csv)

    merged = acc_df.merge(
        rules_df[["scenario_id", "if_then_rule"]],
        on="scenario_id",
        how="left"
    ).merge(
        val_df[[
            "scenario_id",
            "baseline_gtMs",
            "recommended_gtMs",
            "baseline_pdr_mean",
            "recommended_pdr_mean",
            "baseline_delay_mean_ms",
            "recommended_delay_mean_ms",
            "threshold_satisfied"
        ]],
        on="scenario_id",
        how="left"
    )

    merged = merged.sort_values(["srcPpm", "scenario_id"]).reset_index(drop=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(ns3_dir, f"contrib/lora_drift_gt/results/phase5_step3_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    final_table_path = os.path.join(outdir, "phase5_step3_final_recommendation_table.csv")
    merged.to_csv(final_table_path, index=False)

    strategy_matrix = merged[[
        "scenario_id",
        "srcPpm",
        "relayPpm",
        "sinkPpm",
        "selected_gtMs",
        "robust_region_label",
        "threshold_satisfied"
    ]].copy()
    strategy_matrix_path = os.path.join(outdir, "phase5_step3_final_strategy_matrix.csv")
    strategy_matrix.to_csv(strategy_matrix_path, index=False)

    compact_df = merged[[
        "scenario_id",
        "srcPpm",
        "selected_gtMs",
        "baseline_gtMs",
        "recommended_pdr_mean",
        "baseline_pdr_mean",
        "recommended_delay_mean_ms",
        "baseline_delay_mean_ms",
        "threshold_satisfied"
    ]].copy()
    compact_path = os.path.join(outdir, "phase5_step3_final_compact.csv")
    compact_df.to_csv(compact_path, index=False)

    report_path = os.path.join(outdir, "phase5_step3_report.txt")
    with open(report_path, "w") as f:
        f.write("PHASE 5 STEP 3 - FINAL STRATEGY SUMMARY REPORT\n")
        f.write("=============================================\n\n")
        f.write(f"Input acceptable GT summary: {acceptable_csv}\n")
        f.write(f"Input strategy rules: {rules_csv}\n")
        f.write(f"Input strategy map: {map_csv}\n")
        f.write(f"Input validation table: {validation_csv}\n")
        f.write(f"Output folder: {outdir}\n\n")

        f.write("Outputs:\n")
        f.write(f"- {final_table_path}\n")
        f.write(f"- {strategy_matrix_path}\n")
        f.write(f"- {compact_path}\n")
        f.write(f"- {report_path}\n\n")

        f.write("Purpose:\n")
        f.write("- Consolidate final strategy outputs for the manuscript\n")
        f.write("- Present the final recommended GT per drift level\n")
        f.write("- Show threshold satisfaction and baseline comparison in one place\n")

    print("DONE Phase 5 Step 3")
    print("Outdir:", outdir)
    print("Saved:")
    print(" -", final_table_path)
    print(" -", strategy_matrix_path)
    print(" -", compact_path)
    print(" -", report_path)


if __name__ == "__main__":
    main()
