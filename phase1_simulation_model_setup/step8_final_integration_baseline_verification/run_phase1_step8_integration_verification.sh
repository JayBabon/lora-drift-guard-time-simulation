#!/usr/bin/env bash
set -euo pipefail

cd ~/ns-3-dev

rm -f contrib/lora_drift_gt/results/phase1_step8_baseline_fixed.csv
rm -f contrib/lora_drift_gt/results/phase1_step8_baseline_proportional.csv
rm -f contrib/lora_drift_gt/results/phase1_step8_integration_summary.txt
rm -f contrib/lora_drift_gt/evidence/phase1_step8/RUN_FIXED.txt
rm -f contrib/lora_drift_gt/evidence/phase1_step8/RUN_PROPORTIONAL.txt

ln -sf ../contrib/lora_drift_gt/src/lora_drift_gt.cc scratch/lora_drift_gt.cc
mkdir -p contrib/lora_drift_gt/results
mkdir -p contrib/lora_drift_gt/evidence/phase1_step8

./ns3 build

./ns3 run "scratch/lora_drift_gt --gtModel=fixed --intervalS=30 --simTimeS=120 --hopDelayS=0.05 --relayProcDelayS=0.01 --srcPpm=40 --relayPpm=20 --sinkPpm=0 --fixedGtMs=0.20 --seed=1 --run=1 --csv=contrib/lora_drift_gt/results/phase1_step8_baseline_fixed.csv" | tee ~/ns-3-dev/contrib/lora_drift_gt/evidence/phase1_step8/RUN_FIXED.txt

./ns3 run "scratch/lora_drift_gt --gtModel=proportional --intervalS=30 --simTimeS=120 --hopDelayS=0.05 --relayProcDelayS=0.01 --srcPpm=40 --relayPpm=20 --sinkPpm=0 --baseGtMs=0.05 --gainK=0.50 --minGtMs=0.01 --maxGtMs=1.00 --seed=1 --run=1 --csv=contrib/lora_drift_gt/results/phase1_step8_baseline_proportional.csv" | tee ~/ns-3-dev/contrib/lora_drift_gt/evidence/phase1_step8/RUN_PROPORTIONAL.txt

cat ~/ns-3-dev/contrib/lora_drift_gt/results/phase1_step8_baseline_fixed.csv
cat ~/ns-3-dev/contrib/lora_drift_gt/results/phase1_step8_baseline_proportional.csv

cat > ~/ns-3-dev/contrib/lora_drift_gt/results/phase1_step8_integration_summary.txt << 'EOF'
PHASE 1 STEP 8 - FINAL INTEGRATION & BASELINE VERIFICATION
==========================================================

Objective 1 completion check:
- ns-3 environment established
- 6-node tree-based multi-hop mesh implemented
- deterministic parent-child forwarding verified
- synchronization-error-based drift model integrated
- fixed GT model integrated
- proportional GT model integrated
- standardized metrics/logging foundation ready

Baseline verification runs completed:
1) Fixed GT baseline:
   contrib/lora_drift_gt/results/phase1_step8_baseline_fixed.csv
   contrib/lora_drift_gt/evidence/phase1_step8/RUN_FIXED.txt

2) Proportional GT baseline:
   contrib/lora_drift_gt/results/phase1_step8_baseline_proportional.csv
   contrib/lora_drift_gt/evidence/phase1_step8/RUN_PROPORTIONAL.txt
EOF

cat ~/ns-3-dev/contrib/lora_drift_gt/results/phase1_step8_integration_summary.txt
