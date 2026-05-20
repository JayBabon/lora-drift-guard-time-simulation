#!/usr/bin/env bash
set -euo pipefail

NS3_DIR="${NS3_DIR:-${HOME}/ns-3-dev}"
CFG_DIR="${NS3_DIR}/contrib/lora_drift_gt/configs"
EVIDENCE_DIR="${NS3_DIR}/contrib/lora_drift_gt/evidence/phase3_step1"

mkdir -p "${CFG_DIR}" "${EVIDENCE_DIR}"

cat > "${CFG_DIR}/phase3_gt_values_ms.txt" << 'EOF'
0
0.01
0.05
0.10
0.20
0.50
1.00
EOF

cat > "${CFG_DIR}/phase3_gt_range_notes.txt" << 'EOF'
PHASE 3 STEP 1 - GUARD-TIME RANGE CONFIGURATION

Objective 3:
Analyze the effect of guard-time configuration on reliability and efficiency.

Selected GT range:
0 ms
0.01 ms
0.05 ms
0.10 ms
0.20 ms
0.50 ms
1.00 ms

Selection rule:
- fixed increment / discrete GT set
- values chosen to span zero, low, moderate, and larger tolerance windows
- range is manageable for capstone-scale sweep experiments

Why this range is used:
- supports systematic GT sweep evaluation
- allows observation of reliability improvement versus latency overhead
- consistent with the manuscript requirement for a fixed increment guard-time range
EOF

{
  echo "PHASE 3 STEP 1 - GT RANGE CONFIGURATION PROOF"
  echo "============================================="
  date
  echo
  echo "[GT values file]"
  cat "${CFG_DIR}/phase3_gt_values_ms.txt"
  echo
  echo "[GT range notes]"
  cat "${CFG_DIR}/phase3_gt_range_notes.txt"
} | tee "${EVIDENCE_DIR}/RUN_PROOF.txt"

echo "DONE Phase 3 Step 1"
