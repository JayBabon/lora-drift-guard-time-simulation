#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Running Phase 3 Step 1: GT range configuration..."
bash "${ROOT_DIR}/step1_define_gt_range/create_phase3_step1_gt_range.sh"

echo "Running Phase 3 Step 2: GT sweep plan..."
bash "${ROOT_DIR}/step2_gt_variation_sweep_plan/create_phase3_step2_gt_sweep_plan.sh"

echo "Phase 3 configuration files were created."
echo "Run Step 3 or Step 4 sweep scripts from inside ns-3 when ready:"
echo "  bash ${ROOT_DIR}/step3_gt_metrics_sweep_script/run_phase3_step3_gt_sweep.sh"
echo "  bash ${ROOT_DIR}/step4_full_gt_sweep_execution/run_phase3_step4_full.sh"
echo
echo "After Step 4 raw data exists, run:"
echo "  python3 ${ROOT_DIR}/step5_gt_reliability_aggregation/analyze_phase3_step5.py"
echo "  python3 ${ROOT_DIR}/step6_gt_efficiency_tradeoff/analyze_phase3_step6.py"
echo "  python3 ${ROOT_DIR}/step7_gt_impact_interpretation/analyze_phase3_step7.py"
