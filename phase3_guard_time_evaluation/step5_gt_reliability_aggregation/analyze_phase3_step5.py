#!/usr/bin/env python3
import argparse
import glob
import math
import os
from datetime import datetime

import pandas as pd


def latest_raw_csv(ns3_dir: str) -> str:
    pattern = os.path.join(ns3_dir, "contrib/lora_drift_gt/results/phase3_step4_raw_*.csv")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No Phase 3 Step 4 raw CSV found at: {pattern}")
    return files[0]


def ci95_halfwidth(series: pd.Series) -> float:
    s = pd.to_numeric(series, errors="coerce").dropna()
    n = len(s)
    if n <= 1:
        return 0.0
    return 1.96 * (s.std(ddof=1) / math.sqrt(n))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="", help="Path to phase3_step4_raw_*.csv; leave blank to auto-pick latest")
    ap.add_argument("--pdr_target", type=float, default=95.0, help="Reliability target in percent")
    ap.add_argument("--outdir", default="", help="Output directory; default auto timestamp under results/")
    args = ap.parse_args()

    ns3_dir = os.path.expanduser("~/ns-3-dev")
    inp = args.input.strip() or latest_raw_csv(ns3_dir)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = args.outdir.strip() or os.path.join(ns3_dir, f"contrib/lora_drift_gt/results/phase3_step5_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    df = pd.read_csv(inp)

    num_cols = [
        "seed", "run", "srcPpm", "relayPpm", "sinkPpm", "gtMs",
        "tx_total", "relay_rx_total", "relay_rx_ok", "relay_viol",
        "relay_fwd_total", "sink_rx_total", "sink_rx_ok", "sink_viol",
        "pdr_ok_percent", "plr_percent", "avg_delay_ok_ms",
        "avg_gt_used_ok_ms", "total_viol", "violation_rate"
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    group_cols = ["scenario_id", "srcPpm", "relayPpm", "sinkPpm", "gtModel", "gtMs"]
    metrics = ["pdr_ok_percent", "plr_percent", "total_viol", "violation_rate", "avg_delay_ok_ms"]

    summary_rows = []
    for keys, sub in df.groupby(group_cols, dropna=False):
        row = {
            "scenario_id": keys[0],
            "srcPpm": keys[1],
            "relayPpm": keys[2],
            "sinkPpm": keys[3],
            "gtModel": keys[4],
            "gtMs": keys[5],
            "k_runs": int(sub["run"].count())
        }
        for m in metrics:
            s = pd.to_numeric(sub[m], errors="coerce")
            row[f"{m}_mean"] = float(s.mean()) if len(s.dropna()) else 0.0
            row[f"{m}_std"] = float(s.std(ddof=1)) if len(s.dropna()) > 1 else 0.0
            row[f"{m}_median"] = float(s.median()) if len(s.dropna()) else 0.0
            row[f"{m}_ci95_halfwidth"] = float(ci95_halfwidth(s))
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows).sort_values(["srcPpm", "gtMs", "scenario_id"])

    detailed_path = os.path.join(outdir, "phase3_step5_summary_by_drift_gt.csv")
    summary_df.to_csv(detailed_path, index=False)

    compact_cols = [
        "scenario_id", "srcPpm", "relayPpm", "sinkPpm", "gtModel", "gtMs", "k_runs",
        "pdr_ok_percent_mean", "pdr_ok_percent_std", "pdr_ok_percent_ci95_halfwidth",
        "plr_percent_mean", "plr_percent_std",
        "total_viol_mean", "total_viol_std",
        "violation_rate_mean", "violation_rate_std",
        "avg_delay_ok_ms_mean", "avg_delay_ok_ms_std"
    ]
    compact_df = summary_df[compact_cols].copy()
    compact_path = os.path.join(outdir, "phase3_step5_compact_summary.csv")
    compact_df.to_csv(compact_path, index=False)

    target = args.pdr_target
    min_rows = []
    for sid, sub in summary_df.groupby("scenario_id"):
        sub_sorted = sub.sort_values("gtMs")
        ok = sub_sorted[sub_sorted["pdr_ok_percent_mean"] >= target]
        if len(ok) == 0:
            first = sub_sorted.iloc[0]
            min_rows.append({
                "scenario_id": sid,
                "srcPpm": float(first["srcPpm"]),
                "relayPpm": float(first["relayPpm"]),
                "sinkPpm": float(first["sinkPpm"]),
                "pdr_target_percent": target,
                "min_gtMs": None,
                "pdr_mean_at_min_gt": None,
                "violation_rate_mean_at_min_gt": None,
                "delay_mean_ms_at_min_gt": None
            })
        else:
            best = ok.iloc[0]
            min_rows.append({
                "scenario_id": sid,
                "srcPpm": float(best["srcPpm"]),
                "relayPpm": float(best["relayPpm"]),
                "sinkPpm": float(best["sinkPpm"]),
                "pdr_target_percent": target,
                "min_gtMs": float(best["gtMs"]),
                "pdr_mean_at_min_gt": float(best["pdr_ok_percent_mean"]),
                "violation_rate_mean_at_min_gt": float(best["violation_rate_mean"]),
                "delay_mean_ms_at_min_gt": float(best["avg_delay_ok_ms_mean"])
            })

    minmap_df = pd.DataFrame(min_rows).sort_values(["srcPpm", "scenario_id"])
    minmap_path = os.path.join(outdir, "phase3_step5_min_gt_per_drift.csv")
    minmap_df.to_csv(minmap_path, index=False)

    pdr_matrix = summary_df.pivot(index="scenario_id", columns="gtMs", values="pdr_ok_percent_mean").sort_index()
    pdr_matrix_path = os.path.join(outdir, "phase3_step5_pdr_matrix.csv")
    pdr_matrix.to_csv(pdr_matrix_path)

    report_path = os.path.join(outdir, "phase3_step5_report.txt")
    with open(report_path, "w") as f:
        f.write(f"INPUT: {inp}\n")
        f.write(f"PDR_TARGET(%): {target}\n")
        f.write(f"OUTDIR: {outdir}\n\n")
        f.write("Outputs:\n")
        f.write(f"- {detailed_path}\n")
        f.write(f"- {compact_path}\n")
        f.write(f"- {minmap_path}\n")
        f.write(f"- {pdr_matrix_path}\n")
        f.write(f"- {report_path}\n\n")
        f.write("Summary:\n")
        f.write("- GT–reliability summary by drift × GT\n")
        f.write("- Minimum threshold-satisfying GT per drift\n")
        f.write("- PDR matrix for curve/plot preparation\n")

    print("DONE Phase 3 Step 5")
    print("Input:", inp)
    print("Outdir:", outdir)
    print("Saved:")
    for p in [detailed_path, compact_path, minmap_path, pdr_matrix_path, report_path]:
        print(" -", p)


if __name__ == "__main__":
    main()
