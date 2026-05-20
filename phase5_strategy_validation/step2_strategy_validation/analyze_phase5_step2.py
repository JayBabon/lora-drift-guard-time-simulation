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
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase4_step6_*")
    dirs = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    dirs = sorted(dirs, key=os.path.getmtime, reverse=True)
    if not dirs:
        raise FileNotFoundError(f"No Phase 4 Step 6 directory found at: {pattern}")
    return dirs[0]


def main():
    ns3_dir = os.path.expanduser("~/ns-3-dev")
    step5_dir = latest_step5_dir(ns3_dir)
    step6_dir = latest_step6_dir(ns3_dir)

    summary_csv = os.path.join(step5_dir, "phase3_step5_summary_by_drift_gt.csv")
    acceptable_csv = os.path.join(step6_dir, "phase4_step6_acceptable_gt_summary.csv")

    for p in [summary_csv, acceptable_csv]:
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Required file not found: {p}")

    summary_df = pd.read_csv(summary_csv)
    acceptable_df = pd.read_csv(acceptable_csv)

    summary_df = summary_df.sort_values(["srcPpm", "gtMs", "scenario_id"]).copy()
    acceptable_df = acceptable_df.sort_values(["srcPpm", "scenario_id"]).copy()

    baseline_gt = 0.20
    target_pdr = 95.0

    rows = []

    for _, r in acceptable_df.iterrows():
        sid = r["scenario_id"]
        src_ppm = r["srcPpm"]
        relay_ppm = r["relayPpm"]
        sink_ppm = r["sinkPpm"]
        rec_gt = r["selected_gtMs"]

        sub = summary_df[summary_df["scenario_id"] == sid].copy()

        baseline_row = sub[sub["gtMs"].sub(baseline_gt).abs() < 1e-9]
        rec_row = pd.DataFrame()
        if pd.notna(rec_gt):
            rec_row = sub[sub["gtMs"].sub(float(rec_gt)).abs() < 1e-9]

        if len(baseline_row) == 0:
            baseline_pdr = None
            baseline_viol = None
            baseline_delay = None
        else:
            b = baseline_row.iloc[0]
            baseline_pdr = float(b["pdr_ok_percent_mean"])
            baseline_viol = float(b["violation_rate_mean"])
            baseline_delay = float(b["avg_delay_ok_ms_mean"])

        if len(rec_row) == 0:
            rec_pdr = None
            rec_viol = None
            rec_delay = None
            threshold_ok = False
        else:
            rr = rec_row.iloc[0]
            rec_pdr = float(rr["pdr_ok_percent_mean"])
            rec_viol = float(rr["violation_rate_mean"])
            rec_delay = float(rr["avg_delay_ok_ms_mean"])
            threshold_ok = rec_pdr >= target_pdr

        rows.append({
            "scenario_id": sid,
            "srcPpm": src_ppm,
            "relayPpm": relay_ppm,
            "sinkPpm": sink_ppm,
            "baseline_gtMs": baseline_gt,
            "recommended_gtMs": rec_gt,
            "baseline_pdr_mean": baseline_pdr,
            "recommended_pdr_mean": rec_pdr,
            "baseline_violation_rate_mean": baseline_viol,
            "recommended_violation_rate_mean": rec_viol,
            "baseline_delay_mean_ms": baseline_delay,
            "recommended_delay_mean_ms": rec_delay,
            "delta_pdr_recommended_minus_baseline": None if baseline_pdr is None or rec_pdr is None else rec_pdr - baseline_pdr,
            "delta_violation_recommended_minus_baseline": None if baseline_viol is None or rec_viol is None else rec_viol - baseline_viol,
            "delta_delay_recommended_minus_baseline_ms": None if baseline_delay is None or rec_delay is None else rec_delay - baseline_delay,
            "threshold_satisfied": threshold_ok
        })

    val_df = pd.DataFrame(rows).sort_values(["srcPpm", "scenario_id"])

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(ns3_dir, f"contrib/lora_drift_gt/results/phase5_step2_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    validation_path = os.path.join(outdir, "phase5_step2_validation_table.csv")
    val_df.to_csv(validation_path, index=False)

    compact_path = os.path.join(outdir, "phase5_step2_validation_compact.csv")
    val_df[[
        "scenario_id",
        "srcPpm",
        "recommended_gtMs",
        "baseline_gtMs",
        "recommended_pdr_mean",
        "baseline_pdr_mean",
        "recommended_delay_mean_ms",
        "baseline_delay_mean_ms",
        "threshold_satisfied"
    ]].to_csv(compact_path, index=False)

    report_path = os.path.join(outdir, "phase5_step2_report.txt")
    with open(report_path, "w") as f:
        f.write("PHASE 5 STEP 2 - STRATEGY VALIDATION REPORT\n")
        f.write("==========================================\n\n")
        f.write(f"Input GT summary: {summary_csv}\n")
        f.write(f"Input acceptable GT summary: {acceptable_csv}\n")
        f.write(f"Output folder: {outdir}\n\n")

        f.write("Validation rule:\n")
        f.write("- Compare recommended GT against baseline GT = 0.20 ms\n")
        f.write(f"- Check whether recommended GT satisfies PDR target >= {target_pdr}%\n\n")

        f.write("Outputs:\n")
        f.write(f"- {validation_path}\n")
        f.write(f"- {compact_path}\n")
        f.write(f"- {report_path}\n")

    print("DONE Phase 5 Step 2")
    print("Outdir:", outdir)
    print("Saved:")
    print(" -", validation_path)
    print(" -", compact_path)
    print(" -", report_path)


if __name__ == "__main__":
    main()
