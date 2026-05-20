#!/usr/bin/env bash
set -euo pipefail

NS3_DIR="${HOME}/ns-3-dev"
SCRIPT_DIR="${NS3_DIR}/contrib/lora_drift_gt/scripts"

cd "${NS3_DIR}"

python3 "${SCRIPT_DIR}/analyze_phase4_step1.py"
python3 "${SCRIPT_DIR}/analyze_phase4_step2.py"
python3 "${SCRIPT_DIR}/analyze_phase4_step3.py"
python3 "${SCRIPT_DIR}/analyze_phase4_step4.py"
python3 "${SCRIPT_DIR}/analyze_phase4_step5.py"
python3 "${SCRIPT_DIR}/analyze_phase4_step6.py"

echo "DONE Phase 4 all steps"
