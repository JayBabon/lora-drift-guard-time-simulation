#!/usr/bin/env bash
set -euo pipefail

NS3_DIR="${NS3_DIR:-${HOME}/ns-3-dev}"
CFG_DIR="${NS3_DIR}/contrib/lora_drift_gt/configs"
EVIDENCE_DIR="${NS3_DIR}/contrib/lora_drift_gt/evidence/phase3_step2"

mkdir -p "${CFG_DIR}" "${EVIDENCE_DIR}"

cat > "${CFG_DIR}/phase3_gt_sweep_plan.csv" << 'EOF'
scenario_id,srcPpm,relayPpm,sinkPpm,gtMs
D00,0,0,0,0
D00,0,0,0,0.01
D00,0,0,0,0.05
D00,0,0,0,0.10
D00,0,0,0,0.20
D00,0,0,0,0.50
D00,0,0,0,1.00
D20,20,10,0,0
D20,20,10,0,0.01
D20,20,10,0,0.05
D20,20,10,0,0.10
D20,20,10,0,0.20
D20,20,10,0,0.50
D20,20,10,0,1.00
D40,40,20,0,0
D40,40,20,0,0.01
D40,40,20,0,0.05
D40,40,20,0,0.10
D40,40,20,0,0.20
D40,40,20,0,0.50
D40,40,20,0,1.00
D80,80,40,0,0
D80,80,40,0,0.01
D80,80,40,0,0.05
D80,80,40,0,0.10
D80,80,40,0,0.20
D80,80,40,0,0.50
D80,80,40,0,1.00
EOF

cat > "${CFG_DIR}/phase3_gt_variation_method.txt" << 'EOF'
PHASE 3 STEP 2 - GT VARIATION METHOD

Objective 3:
Analyze the effect of guard-time configuration on reliability and efficiency.

Variation method:
- fixed-step GT sweep
- GT values are tested in ascending order
- one run is prepared for each (drift scenario, GT value) pair

Selected GT values:
0
0.01
0.05
0.10
0.20
0.50
1.00 ms

Representative drift scenarios used for the GT study:
- D00: srcPpm=0,  relayPpm=0,  sinkPpm=0
- D20: srcPpm=20, relayPpm=10, sinkPpm=0
- D40: srcPpm=40, relayPpm=20, sinkPpm=0
- D80: srcPpm=80, relayPpm=40, sinkPpm=0

Constant settings for Objective 3 runs:
- topology = 6-node tree-based mesh
- intervalS = 30.0
- simTimeS = 300
- hopDelayS = 0.05
- relayProcDelayS = 0.01
- gtModel = fixed

Objective 3 rule:
- vary GT systematically
- compare reliability and delay across GT values
- keep the rest of the settings fixed for fair comparison
EOF

{
  echo "PHASE 3 STEP 2 - GT VARIATION METHOD PROOF"
  echo "=========================================="
  date
  echo
  echo "[GT sweep plan]"
  cat "${CFG_DIR}/phase3_gt_sweep_plan.csv"
  echo
  echo "[GT variation method]"
  cat "${CFG_DIR}/phase3_gt_variation_method.txt"
} | tee "${EVIDENCE_DIR}/RUN_PROOF.txt"

echo "DONE Phase 3 Step 2"
