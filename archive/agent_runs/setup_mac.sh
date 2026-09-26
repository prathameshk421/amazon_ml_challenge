#!/usr/bin/env bash
# One-time setup. Run it from the STAGING folder (~/Desktop/er-setup) that contains:
#   student_resource/  setup_mac.sh  run_overnight.sh  keep_awake.sh  opencode.json
#   overnight_eda_agent_prompt.md  AGENTS.md  notes/
# Optional: ./setup_mac.sh /path/to/your/data/folder   (folder that contains dataset/ and utils/)
set -euo pipefail

PROJECT="$HOME/amazon-er"
STAGE="$(pwd)"
SRC="${1:-student_resource}"

fail() { echo "ERROR: $*" >&2; exit 1; }

# --- 0. sanity checks on what you downloaded ---------------------------------
[ -d "$SRC" ] || fail "'$SRC' not found in $STAGE. Unzip the dataset here so 'student_resource/' exists."
for f in train_source1.tsv train_source2.tsv train_source3.tsv train_ground_truth.tsv; do
  [ -f "$SRC/dataset/train/$f" ] || fail "$SRC/dataset/train/$f missing. The folder must contain dataset/train and dataset/test."
done
for f in test_source1.tsv test_source2.tsv test_source3.tsv; do
  [ -f "$SRC/dataset/test/$f" ] || fail "$SRC/dataset/test/$f missing"
done
[ -f "$SRC/utils/validate_submission.py" ] || echo "WARNING: $SRC/utils/validate_submission.py missing (the validator). Continuing."
for f in overnight_eda_agent_prompt.md AGENTS.md opencode.json run_overnight.sh keep_awake.sh; do
  [ -f "$f" ] || fail "$f missing from $STAGE"
done
[ -d notes ] || fail "notes/ folder missing from $STAGE"
[ ! -e "$PROJECT" ] || fail "$PROJECT already exists. Rename or delete it first (protects your work)."

# --- 1. tools ------------------------------------------------------------------
xcode-select -p >/dev/null 2>&1 || { echo "Installing Xcode command line tools. Re-run this script when that finishes."; xcode-select --install; exit 1; }
command -v brew >/dev/null || fail "Homebrew missing. Install from https://brew.sh then re-run."
brew install node python@3.11 libomp tmux git
npm install -g opencode-ai

# --- 2. project folder -----------------------------------------------------------
mkdir -p "$PROJECT/src" "$PROJECT/reports" "$PROJECT/logs" "$PROJECT/output/draft" \
         "$PROJECT/artifacts/metrics" "$PROJECT/artifacts/models" "$PROJECT/artifacts/candidates"
cp -R "$SRC" "$PROJECT/student_resource"
cp -R notes "$PROJECT/notes"
cp overnight_eda_agent_prompt.md AGENTS.md opencode.json run_overnight.sh keep_awake.sh "$PROJECT/"
chmod +x "$PROJECT/run_overnight.sh" "$PROJECT/keep_awake.sh"

# --- 3. python env ---------------------------------------------------------------
cd "$PROJECT"
"$(brew --prefix python@3.11)/bin/python3.11" -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install pandas numpy scipy scikit-learn rapidfuzz jellyfish lightgbm sentence-transformers huggingface_hub matplotlib tqdm pyarrow
pip freeze > requirements.txt

# --- 4. goal plugin + git --------------------------------------------------------
npm init -y >/dev/null
npm install opencode-goal-plugin
printf "student_resource/\n.venv/\nnode_modules/\nlogs/\nartifacts/models/\nartifacts/candidates/\n*.parquet\n*.tsv\n" > .gitignore
git init -q
git add -A && git -c user.name=er -c user.email=er@local commit -qm "initial setup"

echo
echo "DONE. Project: $PROJECT"
echo "Sanity check: cd $PROJECT && source .venv/bin/activate && python -c \"import pandas as pd; print(pd.read_csv('student_resource/dataset/train/train_source1.tsv', sep='\\t').shape)\""
echo "Then run:     cd $PROJECT && ./run_overnight.sh"
