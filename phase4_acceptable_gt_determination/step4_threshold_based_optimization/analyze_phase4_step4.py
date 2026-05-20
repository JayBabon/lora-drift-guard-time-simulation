#!/usr/bin/env python3
import glob
import os
from datetime import datetime

import pandas as pd


def latest_step3_dir(ns3_dir: str) -> str:
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase4_step3_*")
    dirs = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    dirs = sorted(dirs, key=os.path.getmtime, reverse=True)
    if not dirs:
        raise FileNotFoundError(f"No Phase 4 Step 3 directory found at: {pattern}")
    return dirs[0]


def main():
    ns3_dir = os.path.expanduser("~/ns-3-dev")
    step3_dir = latest_step3_dir(ns3_dir)

    labeled_csv = os.path.join(step3_dir, "phase4_step3_threshold_interaction_table.csv")
    if not os.path.isfile(labeled_csv):
        raise FileNotFoundError(f"Threshold interaction table not found: {labeled_csv}")

    df = pd.read_csv(labeled_csv)
    df = df.sort_values(["srcPpm", "gtMs", "scenario_id"]).copy()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(ns3_dir, f"contrib/lora_drift_gt/results/phase4_step4_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    rows = []
    for sid, sub in df.groupby("scenario_id"):
        sub = sub.sort_values("gtMs")
        acceptable = sub[sub["region_label"] == "Stable"]

        if len(acceptable) == 0:
            first = sub.iloc[0]
            rows.append({
                "scenario_id": sid,
                "srcPpm": float(first["srcPpm"]),
                "relayPpm": float(first["relayPpm"]),
                "sinkPpm": float(first["sinkPpm"]),
                "selected_gtMs": None,
                "selection_status": "No stable GT found",
                "pdr_mean_at_selected_gt": None,
                "violation_rate_mean_at_selected_gt": None,
                "delay_mean_ms_at_selected_gt": None,
            })
        else:
            best = acceptable.iloc[0]
            rows.append({
                "scenario_id": sid,
                "srcPpm": float(best["srcPpm"]),
                "relayPpm": float(best["relayPpm"]),
                "sinkPpm": float(best["sinkPpm"]),
                "selected_gtMs": float(best["gtMs"]),
                "selection_status": "Selected minimum stable GT",
                "pdr_mean_at_selected_gt": float(best["pdr_ok_percent_mean"]),
                "violation_rate_mean_at_selected_gt": float(best["violation_rate_mean"]),
                "delay_mean_ms_at_selected_gt": float(best["avg_delay_ok_ms_mean"]),
            })

    opt_df = pd.DataFrame(rows).sort_values(["srcPpm", "scenario_id"])

    opt_path = os.path.join(outdir, "phase4_step4_threshold_optimization.csv")
    opt_df.to_csv(opt_path, index=False)

    compact_path = os.path.join(outdir, "phase4_step4_acceptable_gt_compact.csv")
    opt_df[["scenario_id", "srcPpm", "relayPpm", "sinkPpm", "selected_gtMs", "selection_status"]].to_csv(compact_path, index=False)

    report_path = os.path.join(outdir, "phase4_step4_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("PHASE 4 STEP 4 - THRESHOLD-BASED OPTIMIZATION REPORT\n")
        f.write("====================================================\n\n")
        f.write(f"Input labeled interaction table: {labeled_csv}\n")
        f.write(f"Output folder: {outdir}\n\n")
        f.write("Optimization rule:\n")
        f.write("- Select the smallest GT labeled Stable for each drift scenario\n")
        f.write("- If no Stable GT exists, report no acceptable GT under current thresholds\n\n")
        f.write("Outputs:\n")
        f.write(f"- {opt_path}\n")
        f.write(f"- {compact_path}\n")
        f.write(f"- {report_path}\n")

    print("DONE Phase 4 Step 4")
    print("Outdir:", outdir)
    print("Saved:")
    print(" -", opt_path)
    print(" -", compact_path)
    print(" -", report_path)


if __name__ == "__main__":
    main()
