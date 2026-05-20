#!/usr/bin/env bash
set -euo pipefail

NS3_DIR="${NS3_DIR:-${HOME}/ns-3-dev}"
APP="${APP:-scratch/lora_drift_gt}"

CFG_DIR="${NS3_DIR}/contrib/lora_drift_gt/configs"
RES_DIR="${NS3_DIR}/contrib/lora_drift_gt/results"
LOG_DIR="${NS3_DIR}/contrib/lora_drift_gt/logs"
EVID_DIR="${NS3_DIR}/contrib/lora_drift_gt/evidence/phase2_step4"

SCENARIO_CSV="${CFG_DIR}/phase2_drift_scenarios.csv"

K_RUNS="${K_RUNS:-10}"
BASE_SEED="${BASE_SEED:-1}"

INTERVAL_S="${INTERVAL_S:-30.0}"
SIM_TIME_S="${SIM_TIME_S:-300}"
HOP_DELAY_S="${HOP_DELAY_S:-0.05}"
RELAY_PROC_DELAY_S="${RELAY_PROC_DELAY_S:-0.01}"

GT_MODEL="${GT_MODEL:-fixed}"
FIXED_GT_MS="${FIXED_GT_MS:-0.20}"

STAMP="$(date +%Y%m%d_%H%M%S)"
RAW_CSV="${RES_DIR}/phase2_step4_raw_${STAMP}.csv"
RUN_LOG="${LOG_DIR}/phase2_step4_${STAMP}.log"

mkdir -p "${RES_DIR}" "${LOG_DIR}" "${EVID_DIR}"

if [[ ! -f "${SCENARIO_CSV}" ]]; then
  echo "ERROR: Scenario file not found: ${SCENARIO_CSV}"
  echo "Run Phase 2 Step 1 first."
  exit 1
fi

cd "${NS3_DIR}"

echo "Building ns-3 model..." | tee "${RUN_LOG}"
./ns3 build >> "${RUN_LOG}" 2>&1

echo "scenario_id,seed,run,gtModel,srcPpm,relayPpm,sinkPpm,tx_total,relay_rx_total,relay_rx_ok,relay_viol,relay_fwd_total,sink_rx_total,sink_rx_ok,sink_viol,pdr_ok_percent,plr_percent,avg_delay_ok_ms,avg_gt_used_ok_ms" > "${RAW_CSV}"

tail -n +2 "${SCENARIO_CSV}" | while IFS=, read -r scenario_id srcPpm relayPpm sinkPpm description
do
  scenario_id="$(echo "${scenario_id}" | xargs)"
  srcPpm="$(echo "${srcPpm}" | xargs)"
  relayPpm="$(echo "${relayPpm}" | xargs)"
  sinkPpm="$(echo "${sinkPpm}" | xargs)"

  for run in $(seq 1 "${K_RUNS}"); do
    TMP_CSV="$(mktemp "${RES_DIR}/tmp_phase2_step4_XXXXXX.csv")"

    echo "Running scenario=${scenario_id} run=${run}/${K_RUNS}" | tee -a "${RUN_LOG}"

    ./ns3 run "${APP} \
      --gtModel=${GT_MODEL} \
      --intervalS=${INTERVAL_S} \
      --simTimeS=${SIM_TIME_S} \
      --hopDelayS=${HOP_DELAY_S} \
      --relayProcDelayS=${RELAY_PROC_DELAY_S} \
      --srcPpm=${srcPpm} \
      --relayPpm=${relayPpm} \
      --sinkPpm=${sinkPpm} \
      --fixedGtMs=${FIXED_GT_MS} \
      --seed=${BASE_SEED} \
      --run=${run} \
      --csv=${TMP_CSV}" >> "${RUN_LOG}" 2>&1

    tail -n +2 "${TMP_CSV}" | awk -F, -v sid="${scenario_id}" 'BEGIN{OFS=","} {print sid,$0}' >> "${RAW_CSV}"
    rm -f "${TMP_CSV}"
  done
done

{
  echo "PHASE 2 STEP 4 - REPLICATION STRATEGY PROOF"
  echo "==========================================="
  date
  echo
  echo "[Latest raw CSV]"
  echo "${RAW_CSV}"
  head -n 10 "${RAW_CSV}"
  echo
  echo "[Run log]"
  echo "${RUN_LOG}"
  tail -n 20 "${RUN_LOG}"
} | tee "${EVID_DIR}/RUN_PROOF.txt"

echo "DONE Phase 2 Step 4"
echo "RAW_CSV=${RAW_CSV}"
echo "RUN_LOG=${RUN_LOG}"
echo "PROOF=${EVID_DIR}/RUN_PROOF.txt"
