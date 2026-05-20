#!/usr/bin/env python3
import glob
import os
from datetime import datetime

import pandas as pd


def latest_step1_dir(ns3_dir: str) -> str:
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase4_step1_*")
    dirs = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    dirs = sorted(dirs, key=os.path.getmtime, reverse=True)
    if not dirs:
        raise FileNotFoundError(f"No Phase 4 Step 1 directory found at: {pattern}")
    return dirs[0]


def main():
    ns3_dir = os.path.expanduser("~/ns-3-dev")
    step1_dir = latest_step1_dir(ns3_dir)

    master_csv = os.path.join(step1_dir, "phase4_step1_master_drift_gt_dataset.csv")
    if not os.path.isfile(master_csv):
        raise FileNotFoundError(f"Master dataset not found: {master_csv}")

    df = pd.read_csv(master_csv)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(ns3_dir, f"contrib/lora_drift_gt/results/phase4_step2_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    df = df.sort_values(["srcPpm", "gtMs", "scenario_id"]).copy()

    long_cols = [
        "scenario_id", "srcPpm", "relayPpm", "sinkPpm", "gtMs",
        "pdr_ok_percent_mean", "violation_rate_mean", "avg_delay_ok_ms_mean",
        "meets_target", "min_gtMs", "avoidable_gt_overhead_ms",
    ]
    long_df = df[[c for c in long_cols if c in df.columns]].copy()
    long_path = os.path.join(outdir, "phase4_step2_interaction_longform.csv")
    long_df.to_csv(long_path, index=False)

    pdr_matrix = df.pivot(index="scenario_id", columns="gtMs", values="pdr_ok_percent_mean").sort_index()
    pdr_path = os.path.join(outdir, "phase4_step2_matrix_pdr.csv")
    pdr_matrix.to_csv(pdr_path)

    viol_matrix = df.pivot(index="scenario_id", columns="gtMs", values="violation_rate_mean").sort_index()
    viol_path = os.path.join(outdir, "phase4_step2_matrix_violation_rate.csv")
    viol_matrix.to_csv(viol_path)

    delay_matrix = df.pivot(index="scenario_id", columns="gtMs", values="avg_delay_ok_ms_mean").sort_index()
    delay_path = os.path.join(outdir, "phase4_step2_matrix_delay.csv")
    delay_matrix.to_csv(delay_path)

    report_path = os.path.join(outdir, "phase4_step2_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("PHASE 4 STEP 2 - DRIFT x GT INTERACTION MATRIX REPORT\n")
        f.write("=====================================================\n\n")
        f.write(f"Input master dataset: {master_csv}\n")
        f.write(f"Output folder: {outdir}\n\n")
        f.write("Outputs:\n")
        f.write(f"- {long_path}\n")
        f.write(f"- {pdr_path}\n")
        f.write(f"- {viol_path}\n")
        f.write(f"- {delay_path}\n")
        f.write(f"- {report_path}\n\n")
        f.write("Purpose:\n")
        f.write("- Build drift x GT interaction matrices\n")
        f.write("- Compare reliability and timing behavior across the design space\n")
        f.write("- Prepare inputs for threshold interaction analysis\n")

    print("DONE Phase 4 Step 2")
    print("Outdir:", outdir)
    print("Saved:")
    print(" -", long_path)
    print(" -", pdr_path)
    print(" -", viol_path)
    print(" -", delay_path)
    print(" -", report_path)


if __name__ == "__main__":
    main()
