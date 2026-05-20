#!/usr/bin/env python3
import glob
import os
from datetime import datetime

import pandas as pd


def latest_step2_dir(ns3_dir: str) -> str:
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase4_step2_*")
    dirs = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    dirs = sorted(dirs, key=os.path.getmtime, reverse=True)
    if not dirs:
        raise FileNotFoundError(f"No Phase 4 Step 2 directory found at: {pattern}")
    return dirs[0]


def classify_region(pdr: float, viol: float) -> str:
    if pdr >= 95.0 and viol <= 5.0:
        return "Stable"
    if pdr < 80.0 or viol > 20.0:
        return "Failing"
    return "Borderline"


def main():
    ns3_dir = os.path.expanduser("~/ns-3-dev")
    step2_dir = latest_step2_dir(ns3_dir)

    long_csv = os.path.join(step2_dir, "phase4_step2_interaction_longform.csv")
    if not os.path.isfile(long_csv):
        raise FileNotFoundError(f"Interaction long-form CSV not found: {long_csv}")

    df = pd.read_csv(long_csv)
    df = df.sort_values(["srcPpm", "gtMs", "scenario_id"]).copy()

    df["region_label"] = df.apply(
        lambda r: classify_region(float(r["pdr_ok_percent_mean"]), float(r["violation_rate_mean"])),
        axis=1,
    )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(ns3_dir, f"contrib/lora_drift_gt/results/phase4_step3_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    labeled_path = os.path.join(outdir, "phase4_step3_threshold_interaction_table.csv")
    df.to_csv(labeled_path, index=False)

    boundary_rows = []
    for sid, sub in df.groupby("scenario_id"):
        sub = sub.sort_values("gtMs")
        stable_rows = sub[sub["region_label"] == "Stable"]
        borderline_rows = sub[sub["region_label"] == "Borderline"]
        failing_rows = sub[sub["region_label"] == "Failing"]

        boundary_rows.append({
            "scenario_id": sid,
            "srcPpm": float(sub.iloc[0]["srcPpm"]),
            "relayPpm": float(sub.iloc[0]["relayPpm"]),
            "sinkPpm": float(sub.iloc[0]["sinkPpm"]),
            "first_stable_gtMs": float(stable_rows.iloc[0]["gtMs"]) if len(stable_rows) else None,
            "first_borderline_gtMs": float(borderline_rows.iloc[0]["gtMs"]) if len(borderline_rows) else None,
            "first_failing_gtMs": float(failing_rows.iloc[0]["gtMs"]) if len(failing_rows) else None,
            "stable_count": int((sub["region_label"] == "Stable").sum()),
            "borderline_count": int((sub["region_label"] == "Borderline").sum()),
            "failing_count": int((sub["region_label"] == "Failing").sum()),
        })

    boundary_df = pd.DataFrame(boundary_rows).sort_values(["srcPpm", "scenario_id"])
    boundary_path = os.path.join(outdir, "phase4_step3_boundary_summary.csv")
    boundary_df.to_csv(boundary_path, index=False)

    region_matrix = df.pivot(index="scenario_id", columns="gtMs", values="region_label").sort_index()
    region_matrix_path = os.path.join(outdir, "phase4_step3_region_matrix.csv")
    region_matrix.to_csv(region_matrix_path)

    report_path = os.path.join(outdir, "phase4_step3_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("PHASE 4 STEP 3 - THRESHOLD INTERACTION ANALYSIS REPORT\n")
        f.write("=====================================================\n\n")
        f.write(f"Input interaction table: {long_csv}\n")
        f.write(f"Output folder: {outdir}\n\n")
        f.write("Region labeling rule:\n")
        f.write("- Stable: PDR >= 95 and violation_rate <= 5\n")
        f.write("- Borderline: otherwise between stable and failing\n")
        f.write("- Failing: PDR < 80 or violation_rate > 20\n\n")
        f.write("Outputs:\n")
        f.write(f"- {labeled_path}\n")
        f.write(f"- {boundary_path}\n")
        f.write(f"- {region_matrix_path}\n")
        f.write(f"- {report_path}\n\n")
        f.write("Purpose:\n")
        f.write("- Detect breakdown boundaries in the drift x GT design space\n")
        f.write("- Separate stable, borderline, and failing operating regions\n")
        f.write("- Prepare optimization inputs for acceptable-GT determination\n")

    print("DONE Phase 4 Step 3")
    print("Outdir:", outdir)
    print("Saved:")
    print(" -", labeled_path)
    print(" -", boundary_path)
    print(" -", region_matrix_path)
    print(" -", report_path)


if __name__ == "__main__":
    main()
