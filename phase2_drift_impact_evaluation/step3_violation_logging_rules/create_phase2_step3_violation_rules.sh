#!/usr/bin/env bash
set -euo pipefail

NS3_DIR="${NS3_DIR:-${HOME}/ns-3-dev}"
CFG_DIR="${NS3_DIR}/contrib/lora_drift_gt/configs"
EVID_DIR="${NS3_DIR}/contrib/lora_drift_gt/evidence/phase2_step3"

mkdir -p "${CFG_DIR}" "${EVID_DIR}"

cat > "${CFG_DIR}/phase2_violation_analysis_plan.txt" << 'EOF'
PHASE 2 STEP 3 - DRIFT IMPACT EVALUATION METHOD

Objective 2 drift impact evaluation method:
Guard-Time Violation Analysis

Per-packet reception rule:
If |arrival_local - expected_local| <= GT:
    classify as RX_OK
Else:
    classify as VIOL

Interpretation:
- RX_OK = packet arrived within the configured guard-time acceptance window
- VIOL = packet arrival exceeded the configured guard-time acceptance window
- VIOL indicates timing failure caused by drift-induced misalignment

Counts to log per run:
- tx_total
- relay_rx_ok
- relay_viol
- sink_rx_ok
- sink_viol

Derived timing-failure measures:
- total_viol = relay_viol + sink_viol
- violation_rate = (total_viol / tx_total) * 100

Reliability measures linked to this evaluation:
- PDR = (sink_rx_ok / tx_total) * 100
- PLR = 100 - PDR

Objective 2 constant run settings:
- topology = 6-node tree-based mesh
- intervalS = 30.0
- simTimeS = 300
- hopDelayS = 0.05
- relayProcDelayS = 0.01
- gtModel = fixed
- fixedGtMs = 0.20

Objective 2 rule:
Only the drift scenario changes.
All other settings remain fixed to isolate drift impact.
EOF

cat > "${CFG_DIR}/phase2_output_fields.csv" << 'EOF'
field_name,meaning,used_in_objective2
scenario_id,Drift scenario identifier,yes
seed,Seed tag for repeatability,yes
run,Run/replication tag,yes
gtModel,Guard-time model used,yes
srcPpm,Source drift level in ppm,yes
relayPpm,Relay drift level in ppm,yes
sinkPpm,Sink drift level in ppm,yes
tx_total,Total transmitted packets,yes
relay_rx_ok,Packets accepted at relay,yes
relay_viol,Packets classified as violations at relay,yes
relay_fwd_total,Packets forwarded by relay,yes
sink_rx_ok,Packets accepted at sink,yes
sink_viol,Packets classified as violations at sink,yes
pdr_ok_percent,Packet delivery ratio,yes
plr_percent,Packet loss rate,yes
avg_delay_ok_ms,Average delay of successful packets,yes
avg_gt_used_ok_ms,Average GT used for successful packets,optional
total_viol,Total timing-failure violations,yes
violation_rate,Violation rate in percent,yes
EOF

{
  echo "PHASE 2 STEP 3 - DRIFT IMPACT EVALUATION METHOD PROOF"
  echo "====================================================="
  date
  echo
  echo "[Violation analysis plan]"
  cat "${CFG_DIR}/phase2_violation_analysis_plan.txt"
  echo
  echo "[Objective 2 output fields]"
  cat "${CFG_DIR}/phase2_output_fields.csv"
} | tee "${EVID_DIR}/RUN_PROOF.txt"

echo "DONE Phase 2 Step 3"
echo "Violation plan: ${CFG_DIR}/phase2_violation_analysis_plan.txt"
echo "Output fields: ${CFG_DIR}/phase2_output_fields.csv"
echo "Proof file: ${EVID_DIR}/RUN_PROOF.txt"
