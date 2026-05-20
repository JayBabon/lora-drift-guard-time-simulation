#!/usr/bin/env python3
import glob
import os
from datetime import datetime

import pandas as pd


def latest_summary_dir(ns3_dir: str) -> str:
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase2_step6_*")
    dirs = [path for path in glob.glob(pattern) if os.path.isdir(path)]
    dirs = sorted(dirs, key=os.path.getmtime, reverse=True)
    if not dirs:
        raise FileNotFoundError(f"No Phase 2 Step 6 summary directory found at: {pattern}")
    return dirs[0]


def classify_region(pdr_mean: float, violation_rate_mean: float) -> str:
    if pdr_mean >= 95.0 and violation_rate_mean <= 5.0:
        return "Stable"
    if pdr_mean >= 80.0 and violation_rate_mean <= 20.0:
        return "Degrading"
    return "Severe Degradation"


def compare_value(current: float, previous: float, tolerance: float = 1e-9) -> str:
    if previous is None:
        return "baseline"
    if current < previous - tolerance:
        return "decreasing"
    if current > previous + tolerance:
        return "increasing"
    return "no_change"


def main():
    ns3_dir = os.path.expanduser("~/ns-3-dev")
    step6_dir = latest_summary_dir(ns3_dir)

    inp = os.path.join(step6_dir, "phase2_step6_compact_summary.csv")
    if not os.path.isfile(inp):
        raise FileNotFoundError(f"Compact summary not found: {inp}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(ns3_dir, f"contrib/lora_drift_gt/results/phase2_step7_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    df = pd.read_csv(inp)
    df = df.sort_values(["srcPpm", "scenario_id"]).copy()

    trend_rows = []
    prev_pdr = None
    prev_violation_rate = None

    for _, row in df.iterrows():
        pdr = float(row["pdr_ok_percent_mean"])
        plr = float(row["plr_percent_mean"])
        violation_rate = float(row["violation_rate_mean"])
        delay = float(row["avg_delay_ok_ms_mean"])

        pdr_trend = compare_value(pdr, prev_pdr)
        violation_trend = compare_value(violation_rate, prev_violation_rate)

        region = classify_region(pdr, violation_rate)

        trend_rows.append({
            "scenario_id": row["scenario_id"],
            "srcPpm": row["srcPpm"],
            "relayPpm": row["relayPpm"],
            "sinkPpm": row["sinkPpm"],
            "k_runs": row["k_runs"],
            "pdr_mean": pdr,
            "plr_mean": plr,
            "violation_rate_mean": violation_rate,
            "avg_delay_ok_ms_mean": delay,
            "pdr_trend_vs_previous": pdr_trend,
            "violation_trend_vs_previous": violation_trend,
            "region_label": region,
        })

        prev_pdr = pdr
        prev_violation_rate = violation_rate

    trend_df = pd.DataFrame(trend_rows)

    trend_csv = os.path.join(outdir, "phase2_step7_drift_trend_table.csv")
    trend_df.to_csv(trend_csv, index=False)

    drift_map_csv = os.path.join(outdir, "phase2_step7_drift_to_reliability_map.csv")
    drift_map_cols = [
        "scenario_id",
        "srcPpm",
        "relayPpm",
        "sinkPpm",
        "pdr_mean",
        "plr_mean",
        "violation_rate_mean",
        "avg_delay_ok_ms_mean",
        "region_label",
    ]
    trend_df[drift_map_cols].to_csv(drift_map_csv, index=False)

    report_txt = os.path.join(outdir, "phase2_step7_interpretation_report.txt")
    with open(report_txt, "w", encoding="utf-8") as f:
        f.write("PHASE 2 STEP 7 - DRIFT EFFECT INTERPRETATION REPORT\n")
        f.write("===================================================\n\n")
        f.write(f"Input summary: {inp}\n")
        f.write(f"Output folder: {outdir}\n\n")
        f.write("Interpretation basis:\n")
        f.write("- Trend analysis of PDR and PLR\n")
        f.write("- Guard-time violation rate behavior\n")
        f.write("- Delay behavior of successful packets\n")
        f.write("- Region labels: Stable / Degrading / Severe Degradation\n\n")

        if not trend_df.empty:
            first = trend_df.iloc[0]
            last = trend_df.iloc[-1]
            f.write("Overall trend summary:\n")
            f.write(
                f"- Lowest drift scenario: {first['scenario_id']} with "
                f"PDR={first['pdr_mean']:.2f}% and violation rate={first['violation_rate_mean']:.2f}%\n"
            )
            f.write(
                f"- Highest drift scenario: {last['scenario_id']} with "
                f"PDR={last['pdr_mean']:.2f}% and violation rate={last['violation_rate_mean']:.2f}%\n\n"
            )

        f.write("Scenario-by-scenario interpretation:\n")
        for _, row in trend_df.iterrows():
            f.write(
                f"- {row['scenario_id']} "
                f"(srcPpm={row['srcPpm']}, relayPpm={row['relayPpm']}, sinkPpm={row['sinkPpm']}): "
                f"PDR={row['pdr_mean']:.2f}%, "
                f"PLR={row['plr_mean']:.2f}%, "
                f"violation_rate={row['violation_rate_mean']:.2f}%, "
                f"avg_delay={row['avg_delay_ok_ms_mean']:.3f} ms, "
                f"region={row['region_label']}, "
                f"PDR trend vs previous={row['pdr_trend_vs_previous']}, "
                f"violation trend vs previous={row['violation_trend_vs_previous']}\n"
            )

        f.write("\nInterpretation note:\n")
        f.write(
            "As drift increases, decreasing PDR and increasing violation rate indicate growing timing "
            "misalignment and reliability degradation.\n"
        )

    evid_dir = os.path.join(ns3_dir, "contrib/lora_drift_gt/evidence/phase2_step7")
    os.makedirs(evid_dir, exist_ok=True)
    proof_path = os.path.join(evid_dir, "RUN_PROOF.txt")
    with open(proof_path, "w", encoding="utf-8") as f:
        f.write("PHASE 2 STEP 7 - DRIFT EFFECT INTERPRETATION PROOF\n")
        f.write("==================================================\n")
        f.write(f"Input summary: {inp}\n")
        f.write(f"Output directory: {outdir}\n")
        f.write(f"Trend table: {trend_csv}\n")
        f.write(f"Drift-to-reliability map: {drift_map_csv}\n")
        f.write(f"Interpretation report: {report_txt}\n\n")
        f.write("Trend table preview:\n")
        f.write(trend_df.head(10).to_csv(index=False))

    print("DONE Phase 2 Step 7")
    print("Input:", inp)
    print("Outdir:", outdir)
    print("Saved:")
    print(" -", trend_csv)
    print(" -", drift_map_csv)
    print(" -", report_txt)
    print("Proof:", proof_path)


if __name__ == "__main__":
    main()
