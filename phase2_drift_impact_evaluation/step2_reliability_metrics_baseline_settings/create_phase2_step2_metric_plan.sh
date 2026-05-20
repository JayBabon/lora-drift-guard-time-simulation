#!/usr/bin/env bash
set -euo pipefail

NS3_DIR="${NS3_DIR:-${HOME}/ns-3-dev}"
CFG_DIR="${NS3_DIR}/contrib/lora_drift_gt/configs"
EVID_DIR="${NS3_DIR}/contrib/lora_drift_gt/evidence/phase2_step2"

mkdir -p "${CFG_DIR}" "${EVID_DIR}"

cat > "${CFG_DIR}/phase2_metric_plan.txt" << 'EOF'
PHASE 2 STEP 2 - OBJECTIVE 2 MEASUREMENT PLAN

Objective 2:
Evaluate the impact of clock synchronization drift on network reliability.

Primary reliability metrics:
1. PDR (Packet Delivery Ratio)
   PDR = (sink_rx_ok / tx_total) * 100

2. PLR (Packet Loss Rate)
   PLR = 100 - PDR

Drift impact / timing-failure metric:
3. Guard-Time Violation Count
   viol = number of packets classified as timing/guard-time violations

Optional derived timing-failure metric:
4. Guard-Time Violation Rate
   violation_rate = (viol / tx_total) * 100

Supporting metric retained from Objective 1:
5. Average end-to-end delay of successful packets
   avg_delay_ok_ms

Constant baseline settings for Objective 2:
- Topology: 6-node tree-based multi-hop mesh
- intervalS = 30.0
- simTimeS = 300
- hopDelayS = 0.05
- relayProcDelayS = 0.01
- gtModel = fixed
- fixedGtMs = 0.20

Objective 2 rule:
Only drift scenario is varied.
Topology, traffic, and GT setting remain fixed for fair comparison.
EOF

cat > "${CFG_DIR}/phase2_baseline_settings.csv" << 'EOF'
parameter,value,notes
topology,6-node tree-based mesh,Fixed topology from Objective 1
intervalS,30.0,Traffic interval in seconds
simTimeS,300,Simulation time per run in seconds
hopDelayS,0.05,Per-hop propagation delay in seconds
relayProcDelayS,0.01,Relay processing delay in seconds
gtModel,fixed,GT held constant during Objective 2
fixedGtMs,0.20,Fixed GT used while varying drift
metric1,PDR,Primary reliability metric
metric2,PLR,Primary reliability metric
metric3,viol,Guard-time violation count
metric4,violation_rate,Derived timing-failure metric
metric5,avg_delay_ok_ms,Supporting delay metric
EOF

{
  echo "PHASE 2 STEP 2 - OBJECTIVE 2 MEASUREMENT PLAN PROOF"
  echo "==================================================="
  date
  echo
  echo "[Metric plan]"
  cat "${CFG_DIR}/phase2_metric_plan.txt"
  echo
  echo "[Baseline settings]"
  cat "${CFG_DIR}/phase2_baseline_settings.csv"
} | tee "${EVID_DIR}/RUN_PROOF.txt"

echo "DONE Phase 2 Step 2"
echo "Metric plan: ${CFG_DIR}/phase2_metric_plan.txt"
echo "Baseline settings: ${CFG_DIR}/phase2_baseline_settings.csv"
echo "Proof file: ${EVID_DIR}/RUN_PROOF.txt"
