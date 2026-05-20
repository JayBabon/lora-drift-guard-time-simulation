#!/usr/bin/env python3
import glob
import os
from datetime import datetime

import pandas as pd


def latest_step_dir(ns3_dir: str, step: int) -> str:
    pattern = os.path.join(ns3_dir, f"contrib/lora_drift_gt/results/phase3_step{step}_*")
    dirs = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    dirs = sorted(dirs, key=os.path.getmtime, reverse=True)
    if not dirs:
        raise FileNotFoundError(f"No Phase 3 Step {step} directory found at: {pattern}")
    return dirs[0]


def classify_curve_region(sub: pd.DataFrame) -> str:
    sub = sub.sort_values("gtMs")
    first = sub.iloc[0]
    last = sub.iloc[-1]

    pdr_gain = float(last["pdr_ok_percent_mean"]) - float(first["pdr_ok_percent_mean"])
    viol_drop = float(first["violation_rate_mean"]) - float(last["violation_rate_mean"])

    if pdr_gain <= 1.0 and viol_drop <= 1.0:
        return "Little Benefit"
    if pdr_gain >= 10.0 or viol_drop >= 10.0:
        return "Strong Improvement"
    return "Moderate Improvement"


def main():
    ns3_dir = os.path.expanduser("~/ns-3-dev")
    step5_dir = latest_step_dir(ns3_dir, 5)
    step6_dir = latest_step_dir(ns3_dir, 6)

    summary_csv = os.path.join(step5_dir, "phase3_step5_summary_by_drift_gt.csv")
    min_gt_csv = os.path.join(step5_dir, "phase3_step5_min_gt_per_drift.csv")
    costing_csv = os.path.join(step6_dir, "phase3_step6_threshold_costing.csv")
    compact_tradeoff_csv = os.path.join(step6_dir, "phase3_step6_compact_tradeoff.csv")

    for p in [summary_csv, min_gt_csv, costing_csv, compact_tradeoff_csv]:
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Required file not found: {p}")

    summary_df = pd.read_csv(summary_csv)
    min_df = pd.read_csv(min_gt_csv)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(ns3_dir, f"contrib/lora_drift_gt/results/phase3_step7_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    trend_rows = []
    threshold_rows = []

    for sid, sub in summary_df.groupby("scenario_id"):
        sub = sub.sort_values("gtMs").copy()
        first = sub.iloc[0]
        last = sub.iloc[-1]

        pdr_gain = float(last["pdr_ok_percent_mean"]) - float(first["pdr_ok_percent_mean"])
        viol_drop = float(first["violation_rate_mean"]) - float(last["violation_rate_mean"])
        delay_increase = float(last["avg_delay_ok_ms_mean"]) - float(first["avg_delay_ok_ms_mean"])

        region = classify_curve_region(sub)

        threshold_info = min_df[min_df["scenario_id"] == sid]
        if len(threshold_info) == 0:
            min_gt = pd.NA
            threshold_status = "No threshold entry"
        else:
            row = threshold_info.iloc[0]
            min_gt = row["min_gtMs"]
            threshold_status = "Threshold found" if pd.notna(min_gt) else "Threshold not met"

        trend_rows.append({
            "scenario_id": sid,
            "srcPpm": float(first["srcPpm"]),
            "relayPpm": float(first["relayPpm"]),
            "sinkPpm": float(first["sinkPpm"]),
            "curve_region": region,
            "pdr_at_min_tested_gt": float(first["pdr_ok_percent_mean"]),
            "pdr_at_max_tested_gt": float(last["pdr_ok_percent_mean"]),
            "pdr_gain_from_min_to_max_gt": pdr_gain,
            "violation_rate_at_min_tested_gt": float(first["violation_rate_mean"]),
            "violation_rate_at_max_tested_gt": float(last["violation_rate_mean"]),
            "violation_rate_drop_from_min_to_max_gt": viol_drop,
            "delay_at_min_tested_gt_ms": float(first["avg_delay_ok_ms_mean"]),
            "delay_at_max_tested_gt_ms": float(last["avg_delay_ok_ms_mean"]),
            "delay_increase_from_min_to_max_gt_ms": delay_increase,
            "threshold_status": threshold_status,
            "min_threshold_gt_ms": min_gt
        })

        threshold_rows.append({
            "scenario_id": sid,
            "srcPpm": float(first["srcPpm"]),
            "relayPpm": float(first["relayPpm"]),
            "sinkPpm": float(first["sinkPpm"]),
            "threshold_status": threshold_status,
            "min_threshold_gt_ms": min_gt
        })

    trend_df = pd.DataFrame(trend_rows).sort_values(["srcPpm", "scenario_id"])
    threshold_df = pd.DataFrame(threshold_rows).sort_values(["srcPpm", "scenario_id"])

    trend_csv = os.path.join(outdir, "phase3_step7_gt_trend_table.csv")
    threshold_csv = os.path.join(outdir, "phase3_step7_threshold_interpretation.csv")
    report_txt = os.path.join(outdir, "phase3_step7_interpretation_report.txt")

    trend_df.to_csv(trend_csv, index=False)
    threshold_df.to_csv(threshold_csv, index=False)

    with open(report_txt, "w") as f:
        f.write("PHASE 3 STEP 7 - GT IMPACT INTERPRETATION REPORT\n")
        f.write("===============================================\n\n")
        f.write(f"Input Step 5 summary: {summary_csv}\n")
        f.write(f"Input Step 5 min GT map: {min_gt_csv}\n")
        f.write(f"Input Step 6 costing: {costing_csv}\n")
        f.write(f"Input Step 6 compact trade-off: {compact_tradeoff_csv}\n")
        f.write(f"Output folder: {outdir}\n\n")

        f.write("Interpretation basis:\n")
        f.write("- GT trend interpretation\n")
        f.write("- Threshold interpretation\n")
        f.write("- Reliability indicators: PDR and violation rate\n")
        f.write("- Efficiency indicator: average end-to-end delay\n\n")

        for _, r in trend_df.iterrows():
            f.write(
                f"- {r['scenario_id']} (srcPpm={r['srcPpm']}, relayPpm={r['relayPpm']}, sinkPpm={r['sinkPpm']}): "
                f"curve_region={r['curve_region']}, "
                f"PDR from min->max GT = {r['pdr_at_min_tested_gt']:.2f}% -> {r['pdr_at_max_tested_gt']:.2f}% "
                f"(gain={r['pdr_gain_from_min_to_max_gt']:.2f}), "
                f"violation rate from min->max GT = {r['violation_rate_at_min_tested_gt']:.2f}% -> {r['violation_rate_at_max_tested_gt']:.2f}% "
                f"(drop={r['violation_rate_drop_from_min_to_max_gt']:.2f}), "
                f"delay from min->max GT = {r['delay_at_min_tested_gt_ms']:.3f} ms -> {r['delay_at_max_tested_gt_ms']:.3f} ms "
                f"(increase={r['delay_increase_from_min_to_max_gt_ms']:.3f} ms), "
                f"threshold_status={r['threshold_status']}, "
                f"min_threshold_gt_ms={r['min_threshold_gt_ms']}\n"
            )

        f.write("\nInterpretation note:\n")
        f.write("Increasing GT should be interpreted as beneficial while reliability improves or violations decrease meaningfully. Once additional GT produces little reliability benefit but still adds delay, the curve has entered saturation or diminishing-return behavior.\n")

    print("DONE Phase 3 Step 7")
    print("Outdir:", outdir)
    print("Saved:")
    for p in [trend_csv, threshold_csv, report_txt]:
        print(" -", p)


if __name__ == "__main__":
    main()
