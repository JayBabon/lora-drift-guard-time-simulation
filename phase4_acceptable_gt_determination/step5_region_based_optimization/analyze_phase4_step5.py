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


def latest_step4_dir(ns3_dir: str) -> str:
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase4_step4_*")
    dirs = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    dirs = sorted(dirs, key=os.path.getmtime, reverse=True)
    if not dirs:
        raise FileNotFoundError(f"No Phase 4 Step 4 directory found at: {pattern}")
    return dirs[0]


def label_region_width(width_ms: float) -> str:
    if width_ms >= 0.30:
        return "Wide Stable Region"
    if width_ms > 0:
        return "Narrow Stable Region"
    return "Single-Point Stable Region"


def main():
    ns3_dir = os.path.expanduser("~/ns-3-dev")
    step3_dir = latest_step3_dir(ns3_dir)
    step4_dir = latest_step4_dir(ns3_dir)

    labeled_csv = os.path.join(step3_dir, "phase4_step3_threshold_interaction_table.csv")
    opt_csv = os.path.join(step4_dir, "phase4_step4_threshold_optimization.csv")

    for p in [labeled_csv, opt_csv]:
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Required file not found: {p}")

    df = pd.read_csv(labeled_csv)
    opt_df = pd.read_csv(opt_csv)
    df = df.sort_values(["srcPpm", "gtMs", "scenario_id"]).copy()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(ns3_dir, f"contrib/lora_drift_gt/results/phase4_step5_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    rows = []
    for sid, sub in df.groupby("scenario_id"):
        sub = sub.sort_values("gtMs").copy()
        stable = sub[sub["region_label"] == "Stable"]
        borderline = sub[sub["region_label"] == "Borderline"]
        failing = sub[sub["region_label"] == "Failing"]
        first_row = sub.iloc[0]

        if len(stable) == 0:
            rows.append({
                "scenario_id": sid,
                "srcPpm": float(first_row["srcPpm"]),
                "relayPpm": float(first_row["relayPpm"]),
                "sinkPpm": float(first_row["sinkPpm"]),
                "stable_region_exists": False,
                "stable_gt_start_ms": None,
                "stable_gt_end_ms": None,
                "stable_region_width_ms": None,
                "first_borderline_gt_ms": float(borderline.iloc[0]["gtMs"]) if len(borderline) else None,
                "first_failing_gt_ms": float(failing.iloc[0]["gtMs"]) if len(failing) else None,
                "robust_region_label": "No Stable Region",
            })
        else:
            stable_start = float(stable.iloc[0]["gtMs"])
            stable_end = float(stable.iloc[-1]["gtMs"])
            stable_width = stable_end - stable_start
            rows.append({
                "scenario_id": sid,
                "srcPpm": float(first_row["srcPpm"]),
                "relayPpm": float(first_row["relayPpm"]),
                "sinkPpm": float(first_row["sinkPpm"]),
                "stable_region_exists": True,
                "stable_gt_start_ms": stable_start,
                "stable_gt_end_ms": stable_end,
                "stable_region_width_ms": stable_width,
                "first_borderline_gt_ms": float(borderline.iloc[0]["gtMs"]) if len(borderline) else None,
                "first_failing_gt_ms": float(failing.iloc[0]["gtMs"]) if len(failing) else None,
                "robust_region_label": label_region_width(stable_width),
            })

    region_opt_df = pd.DataFrame(rows).sort_values(["srcPpm", "scenario_id"])

    region_opt_path = os.path.join(outdir, "phase4_step5_region_optimization.csv")
    region_opt_df.to_csv(region_opt_path, index=False)

    compact_cols = [
        "scenario_id", "srcPpm", "relayPpm", "sinkPpm", "stable_region_exists",
        "stable_gt_start_ms", "stable_gt_end_ms", "stable_region_width_ms", "robust_region_label",
    ]
    compact_df = region_opt_df[compact_cols].copy()
    compact_path = os.path.join(outdir, "phase4_step5_region_compact.csv")
    compact_df.to_csv(compact_path, index=False)

    merged = region_opt_df.merge(
        opt_df[["scenario_id", "selected_gtMs", "selection_status"]],
        on="scenario_id",
        how="left",
    )
    merged_path = os.path.join(outdir, "phase4_step5_region_with_threshold_selection.csv")
    merged.to_csv(merged_path, index=False)

    report_path = os.path.join(outdir, "phase4_step5_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("PHASE 4 STEP 5 - REGION-BASED OPTIMIZATION REPORT\n")
        f.write("=================================================\n\n")
        f.write(f"Input labeled interaction table: {labeled_csv}\n")
        f.write(f"Input threshold optimization: {opt_csv}\n")
        f.write(f"Output folder: {outdir}\n\n")
        f.write("Region-based optimization rule:\n")
        f.write("- Stable region = all GT values labeled Stable under a drift scenario\n")
        f.write("- Operating margin = stable_gt_end_ms - stable_gt_start_ms\n")
        f.write("- Wide/Narrow/Single-Point labels summarize robustness of the acceptable region\n\n")
        f.write("Outputs:\n")
        f.write(f"- {region_opt_path}\n")
        f.write(f"- {compact_path}\n")
        f.write(f"- {merged_path}\n")
        f.write(f"- {report_path}\n")

    print("DONE Phase 4 Step 5")
    print("Outdir:", outdir)
    print("Saved:")
    print(" -", region_opt_path)
    print(" -", compact_path)
    print(" -", merged_path)
    print(" -", report_path)


if __name__ == "__main__":
    main()
