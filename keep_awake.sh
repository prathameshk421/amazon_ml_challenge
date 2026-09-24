#!/usr/bin/env bash
# Keeps the Mac awake for 9 hours (then releases automatically). Leave this Terminal window open.
# -d display  -i idle  -m disk  -s system (works only on AC power). The lid must stay OPEN.
echo "Keeping Mac awake for 9h. Close this window or press Ctrl-C to stop. Lid must stay open, charger plugged in."
exec caffeinate -dims -t 32400
