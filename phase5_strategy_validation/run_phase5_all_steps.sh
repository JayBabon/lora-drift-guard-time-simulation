#!/usr/bin/env bash
set -euo pipefail

NS3_DIR="${HOME}/ns-3-dev"
SCRIPT_DIR="${NS3_DIR}/contrib/lora_drift_gt/scripts"

echo "Running Phase 5 Step 1: Strategy formulation"
python3 "${SCRIPT_DIR}/analyze_phase5_step1.py"

echo "Running Phase 5 Step 2: Strategy validation"
python3 "${SCRIPT_DIR}/analyze_phase5_step2.py"

echo "Running Phase 5 Step 3: Final strategy summary"
python3 "${SCRIPT_DIR}/analyze_phase5_step3.py"

echo "DONE Phase 5 all steps"
