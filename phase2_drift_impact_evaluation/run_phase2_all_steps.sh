#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "${SCRIPT_DIR}/step1_define_drift_scenarios/create_phase2_step1_drift_scenarios.sh"
bash "${SCRIPT_DIR}/step2_reliability_metrics_baseline_settings/create_phase2_step2_metric_plan.sh"
bash "${SCRIPT_DIR}/step3_violation_logging_rules/create_phase2_step3_violation_rules.sh"

# Step 4 is a pre-check / replication setup script.
# To run only one pre-check replication, keep K_RUNS=1.
K_RUNS="${K_RUNS:-1}" BASE_SEED="${BASE_SEED:-1}" \
  bash "${SCRIPT_DIR}/step4_replication_strategy_batch_run/run_phase2_step4_replications.sh"

# Step 5 is the full Objective 2 execution.
# Default K_RUNS=10 if not overridden.
K_RUNS="${FULL_K_RUNS:-10}" BASE_SEED="${BASE_SEED:-1}" \
  bash "${SCRIPT_DIR}/step5_full_drift_experiment_execution/run_phase2_step5_full.sh"

python3 "${SCRIPT_DIR}/step6_statistical_aggregation/analyze_phase2_step6.py"
python3 "${SCRIPT_DIR}/step7_drift_trend_interpretation/analyze_phase2_step7.py"

echo "DONE Phase 2 all steps."
