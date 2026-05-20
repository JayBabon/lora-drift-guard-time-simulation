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


def main():
    ns3_dir = os.path.expanduser("~/ns-3-dev")
    step5_dir = latest_step5_dir(ns3_dir)

    summary_csv = os.path.join(step5_dir, "phase3_step5_summary_by_drift_gt.csv")
    min_gt_csv = os.path.join(step5_dir, "phase3_step5_min_gt_per_drift.csv")

    if not os.path.isfile(summary_csv):
        raise FileNotFoundError(f"Summary CSV not found: {summary_csv}")
    if not os.path.isfile(min_gt_csv):
        raise FileNotFoundError(f"Minimum GT CSV not found: {min_gt_csv}")

    summary_df = pd.read_csv(summary_csv)
    min_df = pd.read_csv(min_gt_csv)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(ns3_dir, f"contrib/lora_drift_gt/results/phase3_step6_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    merged = summary_df.merge(
        min_df[["scenario_id", "min_gtMs", "pdr_target_percent"]],
        on="scenario_id",
        how="left"
    )

    merged["meets_target"] = merged["pdr_ok_percent_mean"] >= merged["pdr_target_percent"]
    merged["avoidable_gt_overhead_ms"] = merged["gtMs"] - merged["min_gtMs"]
    merged.loc[merged["min_gtMs"].isna(), "avoidable_gt_overhead_ms"] = pd.NA

    latency_cols = [
        "scenario_id", "srcPpm", "relayPpm", "sinkPpm", "gtModel", "gtMs", "k_runs",
        "avg_delay_ok_ms_mean", "avg_delay_ok_ms_std", "avg_delay_ok_ms_median",
        "avg_delay_ok_ms_ci95_halfwidth"
    ]
    latency_df = merged[latency_cols].copy().sort_values(["srcPpm", "gtMs", "scenario_id"])
    latency_path = os.path.join(outdir, "phase3_step6_latency_by_drift_gt.csv")
    latency_df.to_csv(latency_path, index=False)

    costing_cols = [
        "scenario_id", "srcPpm", "relayPpm", "sinkPpm",
        "pdr_target_percent", "min_gtMs", "gtMs",
        "pdr_ok_percent_mean", "violation_rate_mean",
        "avg_delay_ok_ms_mean", "meets_target", "avoidable_gt_overhead_ms"
    ]
    costing_df = merged[costing_cols].copy().sort_values(["srcPpm", "gtMs", "scenario_id"])
    costing_path = os.path.join(outdir, "phase3_step6_threshold_costing.csv")
    costing_df.to_csv(costing_path, index=False)

    compact_rows = []
    for sid, sub in merged.groupby("scenario_id"):
        sub = sub.sort_values("gtMs")
        valid_min = sub[sub["gtMs"] == sub["min_gtMs"]]
        if len(valid_min) == 0:
            continue
        best = valid_min.iloc[0]
        max_gt_row = sub.iloc[-1]

        compact_rows.append({
            "scenario_id": sid,
            "srcPpm": best["srcPpm"],
            "relayPpm": best["relayPpm"],
            "sinkPpm": best["sinkPpm"],
            "pdr_target_percent": best["pdr_target_percent"],
            "min_gtMs": best["min_gtMs"],
            "delay_at_min_gt_ms": best["avg_delay_ok_ms_mean"],
            "max_tested_gtMs": max_gt_row["gtMs"],
            "delay_at_max_gt_ms": max_gt_row["avg_delay_ok_ms_mean"],
            "extra_gt_margin_ms": (max_gt_row["gtMs"] - best["min_gtMs"]) if pd.notna(best["min_gtMs"]) else pd.NA,
            "extra_delay_from_min_to_max_ms": (max_gt_row["avg_delay_ok_ms_mean"] - best["avg_delay_ok_ms_mean"])
        })

    compact_df = pd.DataFrame(compact_rows)
    if not compact_df.empty:
        compact_df = compact_df.sort_values(["srcPpm", "scenario_id"])

    compact_path = os.path.join(outdir, "phase3_step6_compact_tradeoff.csv")
    compact_df.to_csv(compact_path, index=False)

    report_path = os.path.join(outdir, "phase3_step6_report.txt")
    with open(report_path, "w") as f:
        f.write("PHASE 3 STEP 6 - GT EFFICIENCY TRADE-OFF REPORT\n")
        f.write("===============================================\n\n")
        f.write(f"Input summary: {summary_csv}\n")
        f.write(f"Input minimum GT map: {min_gt_csv}\n")
        f.write(f"Output folder: {outdir}\n\n")
        f.write("Outputs:\n")
        f.write(f"- {latency_path}\n")
        f.write(f"- {costing_path}\n")
        f.write(f"- {compact_path}\n")
        f.write(f"- {report_path}\n\n")
        f.write("Trade-off method:\n")
        f.write("- GT–latency curve preparation\n")
        f.write("- Reliability threshold costing\n")
        f.write("- Avoidable overhead = GT - minimum threshold-satisfying GT\n\n")

        if not compact_df.empty:
            f.write("Compact trade-off summary:\n")
            for _, r in compact_df.iterrows():
                f.write(
                    f"- {r['scenario_id']} (srcPpm={r['srcPpm']}, relayPpm={r['relayPpm']}, sinkPpm={r['sinkPpm']}): "
                    f"min_gtMs={r['min_gtMs']}, delay_at_min_gt_ms={r['delay_at_min_gt_ms']}, "
                    f"max_tested_gtMs={r['max_tested_gtMs']}, delay_at_max_gt_ms={r['delay_at_max_gt_ms']}, "
                    f"extra_gt_margin_ms={r['extra_gt_margin_ms']}, "
                    f"extra_delay_from_min_to_max_ms={r['extra_delay_from_min_to_max_ms']}\n"
                )
        else:
            f.write("No threshold-satisfying GT was found for any scenario, so no compact trade-off rows were generated.\n")

    print("DONE Phase 3 Step 6")
    print("Input summary:", summary_csv)
    print("Input min GT:", min_gt_csv)
    print("Outdir:", outdir)
    print("Saved:")
    for p in [latency_path, costing_path, compact_path, report_path]:
        print(" -", p)


if __name__ == "__main__":
    main()
