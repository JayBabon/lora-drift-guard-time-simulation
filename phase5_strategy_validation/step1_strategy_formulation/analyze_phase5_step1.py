#!/usr/bin/env python3
import glob
import os
from datetime import datetime

import pandas as pd


def latest_step6_dir(ns3_dir: str) -> str:
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase4_step6_*")
    dirs = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    dirs = sorted(dirs, key=os.path.getmtime, reverse=True)
    if not dirs:
        raise FileNotFoundError(f"No Phase 4 Step 6 directory found at: {pattern}")
    return dirs[0]


def drift_label(src_ppm: float) -> str:
    if src_ppm <= 0:
        return "No Drift"
    if src_ppm <= 20:
        return "Moderate Drift"
    if src_ppm <= 40:
        return "High Drift"
    return "Very High Drift"


def main():
    ns3_dir = os.path.expanduser("~/ns-3-dev")
    step6_dir = latest_step6_dir(ns3_dir)

    summary_csv = os.path.join(step6_dir, "phase4_step6_acceptable_gt_summary.csv")
    if not os.path.isfile(summary_csv):
        raise FileNotFoundError(f"Acceptable GT summary not found: {summary_csv}")

    df = pd.read_csv(summary_csv)
    df = df.sort_values(["srcPpm", "scenario_id"]).copy()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(ns3_dir, f"contrib/lora_drift_gt/results/phase5_step1_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    rules = []
    mapping = []

    for _, r in df.iterrows():
        dlabel = drift_label(float(r["srcPpm"]))
        selected_gt = r["selected_gtMs"]
        robust_label = r.get("robust_region_label", "")
        status = r["selection_status"]

        if pd.isna(selected_gt):
            rule_text = (
                f"If drift condition is {dlabel} "
                f"(srcPpm={r['srcPpm']}, relayPpm={r['relayPpm']}, sinkPpm={r['sinkPpm']}), "
                f"then no acceptable GT recommendation is available under the current thresholds."
            )
        else:
            rule_text = (
                f"If drift condition is {dlabel} "
                f"(srcPpm={r['srcPpm']}, relayPpm={r['relayPpm']}, sinkPpm={r['sinkPpm']}), "
                f"then set guard time to {selected_gt} ms "
                f"because this is the minimum acceptable GT under the evaluated threshold, "
                f"with region label '{robust_label}'."
            )

        rules.append({
            "scenario_id": r["scenario_id"],
            "srcPpm": r["srcPpm"],
            "relayPpm": r["relayPpm"],
            "sinkPpm": r["sinkPpm"],
            "drift_label": dlabel,
            "recommended_gtMs": selected_gt,
            "selection_status": status,
            "robust_region_label": robust_label,
            "if_then_rule": rule_text
        })

        mapping.append({
            "scenario_id": r["scenario_id"],
            "drift_label": dlabel,
            "srcPpm": r["srcPpm"],
            "relayPpm": r["relayPpm"],
            "sinkPpm": r["sinkPpm"],
            "recommended_gtMs": selected_gt,
            "robust_region_label": robust_label
        })

    rules_df = pd.DataFrame(rules).sort_values(["srcPpm", "scenario_id"])
    map_df = pd.DataFrame(mapping).sort_values(["srcPpm", "scenario_id"])

    rules_path = os.path.join(outdir, "phase5_step1_strategy_rules.csv")
    map_path = os.path.join(outdir, "phase5_step1_threshold_strategy_map.csv")
    report_path = os.path.join(outdir, "phase5_step1_report.txt")

    rules_df.to_csv(rules_path, index=False)
    map_df.to_csv(map_path, index=False)

    with open(report_path, "w") as f:
        f.write("PHASE 5 STEP 1 - STRATEGY FORMULATION REPORT\n")
        f.write("===========================================\n\n")
        f.write(f"Input acceptable GT summary: {summary_csv}\n")
        f.write(f"Output folder: {outdir}\n\n")

        f.write("Outputs:\n")
        f.write(f"- {rules_path}\n")
        f.write(f"- {map_path}\n")
        f.write(f"- {report_path}\n\n")

        f.write("Purpose:\n")
        f.write("- Convert acceptable-GT results into if-then decision rules\n")
        f.write("- Build threshold-based strategy mapping from drift level to recommended GT\n")
        f.write("- Prepare strategy outputs for validation in the next step\n")

    print("DONE Phase 5 Step 1")
    print("Outdir:", outdir)
    print("Saved:")
    print(" -", rules_path)
    print(" -", map_path)
    print(" -", report_path)


if __name__ == "__main__":
    main()
