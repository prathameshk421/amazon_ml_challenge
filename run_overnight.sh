#!/usr/bin/env bash
# Starts opencode inside tmux with the Mac kept awake. Run from ~/amazon-er.
# caffeinate -d display, -i idle, -m disk, -s system (AC power only). Lid must stay OPEN.
set -euo pipefail
cd "$(dirname "$0")"
tmux new-session -A -s er "caffeinate -dims opencode; exec bash"
