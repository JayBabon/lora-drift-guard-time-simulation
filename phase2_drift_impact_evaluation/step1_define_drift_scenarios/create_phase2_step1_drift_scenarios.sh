#!/usr/bin/env bash
set -euo pipefail

NS3_DIR="${NS3_DIR:-${HOME}/ns-3-dev}"
CFG_DIR="${NS3_DIR}/contrib/lora_drift_gt/configs"
EVID_DIR="${NS3_DIR}/contrib/lora_drift_gt/evidence/phase2_step1"

mkdir -p "${CFG_DIR}" "${EVID_DIR}"

cat > "${CFG_DIR}/phase2_drift_scenarios.csv" << 'EOF'
scenario_id,srcPpm,relayPpm,sinkPpm,description
D00,0,0,0,No-drift baseline
D10,10,5,0,Low drift scenario
D20,20,10,0,Moderate drift scenario
D40,40,20,0,High drift scenario
D80,80,40,0,Very high drift scenario
EOF

cat > "${CFG_DIR}/phase2_drift_notes.txt" << 'EOF'
PHASE 2 STEP 1 - DRIFT SCENARIO MODELING

Objective:
Define the fixed drift scenarios for Objective 2.

Scenario design rule:
- Fixed ppm levels per scenario
- Drift remains constant within a scenario
- Sink/Root is the timing reference (sinkPpm = 0)

Selected scenarios:
D00: srcPpm=0,  relayPpm=0,  sinkPpm=0
D10: srcPpm=10, relayPpm=5,  sinkPpm=0
D20: srcPpm=20, relayPpm=10, sinkPpm=0
D40: srcPpm=40, relayPpm=20, sinkPpm=0
D80: srcPpm=80, relayPpm=40, sinkPpm=0
EOF

{
  echo "PHASE 2 STEP 1 - DRIFT SCENARIO MODELING PROOF"
  echo "=============================================="
  date
  echo
  echo "[Drift scenario file]"
  cat "${CFG_DIR}/phase2_drift_scenarios.csv"
  echo
  echo "[Scenario notes]"
  cat "${CFG_DIR}/phase2_drift_notes.txt"
} | tee "${EVID_DIR}/RUN_PROOF.txt"

echo "DONE Phase 2 Step 1"
echo "Scenario file: ${CFG_DIR}/phase2_drift_scenarios.csv"
echo "Proof file: ${EVID_DIR}/RUN_PROOF.txt"
