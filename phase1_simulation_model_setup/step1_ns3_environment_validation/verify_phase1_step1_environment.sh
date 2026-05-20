#!/usr/bin/env bash
set -euo pipefail

cd ~/ns-3-dev

git checkout capstone-restart-v1
git status
git branch
git log -1 --oneline

./ns3 clean || true
rm -rf build cmake-cache

./ns3 configure --build-profile=debug --enable-examples --enable-tests
./ns3 build
./ns3 run hello-simulator

mkdir -p ~/ns-3-dev/docs/evidence/phase1_step1
{
  echo "=== Phase 1 Step 1 Evidence (ns-3 Environment Validation) ==="
  date
  echo
  echo "=== System ==="
  lsb_release -a 2>/dev/null || true
  uname -a
  echo
  echo "=== Tool Versions ==="
  g++ --version | head -n 1
  python3 --version
  cmake --version | head -n 1
  git --version
  echo
  echo "=== ns-3 Repo State ==="
  pwd
  git rev-parse --abbrev-ref HEAD
  git log -1 --oneline
  echo
  echo "=== hello-simulator Output ==="
  ./ns3 run hello-simulator
} | tee ~/ns-3-dev/docs/evidence/phase1_step1/VERIFY_PHASE1_STEP1.txt

find ~/ns-3-dev -maxdepth 3 -name compile_commands.json
mkdir -p ~/ns-3-dev/.vscode
cat > ~/ns-3-dev/.vscode/settings.json <<'EOF'
{
  "C_Cpp.default.compileCommands": "${workspaceFolder}/cmake-cache/compile_commands.json",
  "C_Cpp.default.intelliSenseMode": "linux-gcc-x64",
  "files.associations": {
    "*.h": "cpp",
    "*.cc": "cpp"
  }
}
EOF

./ns3 build
./ns3 run hello-simulator
find ~/ns-3-dev -maxdepth 3 -name compile_commands.json
