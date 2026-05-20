#!/usr/bin/env bash
set -euo pipefail

NS3_DIR="${NS3_DIR:-${HOME}/ns-3-dev}"
APP="${APP:-scratch/lora_drift_gt}"

CFG_DIR="${NS3_DIR}/contrib/lora_drift_gt/configs"
RES_DIR="${NS3_DIR}/contrib/lora_drift_gt/results"
LOG_DIR="${NS3_DIR}/contrib/lora_drift_gt/logs"
EVIDENCE_DIR="${NS3_DIR}/contrib/lora_drift_gt/evidence/phase3_step4"

SWEEP_PLAN="${CFG_DIR}/phase3_gt_sweep_plan.csv"

K_RUNS="${K_RUNS:-10}"
BASE_SEED="${BASE_SEED:-1}"

INTERVAL_S="${INTERVAL_S:-30.0}"
SIM_TIME_S="${SIM_TIME_S:-300}"
HOP_DELAY_S="${HOP_DELAY_S:-0.05}"
RELAY_PROC_DELAY_S="${RELAY_PROC_DELAY_S:-0.01}"

GT_MODEL="${GT_MODEL:-fixed}"

STAMP="$(date +%Y%m%d_%H%M%S)"
RAW_CSV="${RES_DIR}/phase3_step4_raw_${STAMP}.csv"
RUN_LOG="${LOG_DIR}/phase3_step4_${STAMP}.log"

mkdir -p "${RES_DIR}" "${LOG_DIR}" "${EVIDENCE_DIR}"

if [[ ! -f "${SWEEP_PLAN}" ]]; then
  echo "ERROR: Sweep plan not found: ${SWEEP_PLAN}"
  echo "Run Phase 3 Step 2 first."
  exit 1
fi

cd "${NS3_DIR}"

echo "Building ns-3 model..." | tee "${RUN_LOG}"
./ns3 build >> "${RUN_LOG}" 2>&1

echo "scenario_id,seed,run,gtModel,srcPpm,relayPpm,sinkPpm,gtMs,tx_total,relay_rx_total,relay_rx_ok,relay_viol,relay_fwd_total,sink_rx_total,sink_rx_ok,sink_viol,pdr_ok_percent,plr_percent,avg_delay_ok_ms,avg_gt_used_ok_ms,total_viol,violation_rate" > "${RAW_CSV}"

tail -n +2 "${SWEEP_PLAN}" | while IFS=, read -r scenario_id srcPpm relayPpm sinkPpm gtMs
do
  scenario_id="$(echo "${scenario_id}" | xargs)"
  srcPpm="$(echo "${srcPpm}" | xargs)"
  relayPpm="$(echo "${relayPpm}" | xargs)"
  sinkPpm="$(echo "${sinkPpm}" | xargs)"
  gtMs="$(echo "${gtMs}" | xargs)"

  for run in $(seq 1 "${K_RUNS}"); do
    TMP_CSV="$(mktemp "${RES_DIR}/tmp_phase3_step4_XXXXXX.csv")"

    echo "Running scenario=${scenario_id} gtMs=${gtMs} run=${run}/${K_RUNS}" | tee -a "${RUN_LOG}"

    ./ns3 run "${APP} \
      --gtModel=${GT_MODEL} \
      --intervalS=${INTERVAL_S} \
      --simTimeS=${SIM_TIME_S} \
      --hopDelayS=${HOP_DELAY_S} \
      --relayProcDelayS=${RELAY_PROC_DELAY_S} \
      --srcPpm=${srcPpm} \
      --relayPpm=${relayPpm} \
      --sinkPpm=${sinkPpm} \
      --fixedGtMs=${gtMs} \
      --seed=${BASE_SEED} \
      --run=${run} \
      --csv=${TMP_CSV}" >> "${RUN_LOG}" 2>&1

    tail -n +2 "${TMP_CSV}" | awk -F, -v sid="${scenario_id}" -v g="${gtMs}" '
      BEGIN{OFS=","}
      {
        total_viol = $10 + $14;
        violation_rate = ($7 == 0 ? 0 : (100.0 * total_viol / $7));
        print sid,$1,$2,$3,$4,$5,$6,g,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,total_viol,violation_rate
      }' >> "${RAW_CSV}"

    rm -f "${TMP_CSV}"
  done
done

{
  echo "PHASE 3 STEP 4 - FULL GT SWEEP EXECUTION PROOF"
  echo "=============================================="
  date
  echo
  echo "[Execution script output]"
  echo "RAW_CSV=${RAW_CSV}"
  echo "RUN_LOG=${RUN_LOG}"
  echo
  echo "[Row count]"
  wc -l "${RAW_CSV}"
  echo
  echo "[Scenario counts]"
  cut -d, -f1 "${RAW_CSV}" | sort | uniq -c
  echo
  echo "[Raw CSV preview]"
  head -n 15 "${RAW_CSV}"
  echo
  echo "[Latest run log tail]"
  tail -n 20 "${RUN_LOG}"
} | tee "${EVIDENCE_DIR}/RUN_PROOF.txt"

echo "DONE Phase 3 Step 4"
echo "RAW_CSV=${RAW_CSV}"
echo "RUN_LOG=${RUN_LOG}"
