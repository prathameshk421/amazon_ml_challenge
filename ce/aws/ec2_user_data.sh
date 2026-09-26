#!/bin/bash
# EC2 user-data for ce_rec_base (same job as Kaggle k2: smoke -> 1 epoch -> score MATCH_VALID/MATCH_TRAIN/TEST).
# Runs as root on a Deep Learning AMI (PyTorch, Ubuntu). Reads s3://__BUCKET__/pairs/, writes s3://__BUCKET__/out/,
# syncs its log to s3://__BUCKET__/logs/ every 2 min, then powers off (instance set to terminate on shutdown).
# Hard cap: the job is killed after __MAX_HOURS__ h so a hang cannot keep billing.
set -uo pipefail
B=s3://__BUCKET__
LOG=/var/log/ce_job.log
exec > >(tee -a $LOG) 2>&1
echo "$(date -Is) start on $(curl -s http://169.254.169.254/latest/meta-data/instance-type)"
( while true; do aws s3 cp $LOG $B/logs/ce_job.log --quiet; sleep 120; done ) &
SYNC=$!

finish() {
  echo "$(date -Is) finish (exit $1)"
  aws s3 sync /opt/ce/work $B/out/ --exclude "*/parts/*" --exclude "smoke/*" --quiet
  aws s3 cp $LOG $B/logs/ce_job.log --quiet
  kill $SYNC 2>/dev/null
  shutdown -h now
}

mkdir -p /opt/ce/input/pairs /opt/ce/work
aws s3 sync $B/pairs/ /opt/ce/input/pairs/ --quiet || finish 11
nvidia-smi

# Python env of the DLAMI (path differs between AMI releases)
for a in /opt/pytorch/bin/activate /opt/conda/bin/activate; do [ -f "$a" ] && source "$a" && break; done
python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())" || finish 12
pip install -q "transformers>=4.45" huggingface_hub pyarrow pandas scikit-learn || finish 13

cd /opt/ce/input/pairs
JOB=train_score CE_INPUT=/opt/ce/input CE_WORK=/opt/ce/work PYTHONUNBUFFERED=1 \
  timeout __MAX_HOURS__h python -u kaggle_run.py
finish $?
