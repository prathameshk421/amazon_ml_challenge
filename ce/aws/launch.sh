#!/bin/bash
# Launch the ce_rec_base job on one EC2 GPU instance (see ec2_user_data.sh). Run from the repo root.
#
#   bash ce/aws/launch.sh setup     # private S3 bucket + upload pairs/scripts + IAM role/instance profile
#   bash ce/aws/launch.sh run       # start the instance (terminates itself when done)
#   bash ce/aws/launch.sh watch     # every 5 min: instance state + last lines of the job log from S3
#   bash ce/aws/launch.sh fetch     # download outputs to work/ce/aws_out/
#
# Env: REGION (ap-south-1), ITYPE (g5.xlarge; fallback g4dn.xlarge), MAX_HOURS (6).
# Every step appends to logs/aws_ce_<step>_<time>.log.
set -euo pipefail
REGION=${REGION:-ap-south-1}
ITYPE=${ITYPE:-g5.xlarge}
MAX_HOURS=${MAX_HOURS:-6}
ACCT=$(aws sts get-caller-identity --query Account --output text)
BUCKET=ber-ce-${ACCT}-${REGION}
ROLE=ber-ce-ec2
TAG=ber-ce-rec-base
STEP=${1:?setup|run|watch|fetch}
mkdir -p logs
LOG=logs/aws_ce_${STEP}_$(date +%Y%m%d_%H%M%S).log
exec > >(tee -a "$LOG") 2>&1
echo "log: $LOG  region=$REGION itype=$ITYPE bucket=$BUCKET"

case $STEP in
setup)
  aws s3api head-bucket --bucket $BUCKET 2>/dev/null || \
    aws s3api create-bucket --bucket $BUCKET --region $REGION --create-bucket-configuration LocationConstraint=$REGION
  aws s3api put-public-access-block --bucket $BUCKET --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  aws s3 sync work/ce/kaggle/pairs/ s3://$BUCKET/pairs/ --exclude "dataset-metadata.json"
  aws s3 cp ce/kaggle/kaggle_run.py s3://$BUCKET/pairs/kaggle_run.py
  if ! aws iam get-role --role-name $ROLE >/dev/null 2>&1; then
    aws iam create-role --role-name $ROLE --assume-role-policy-document \
      '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
    aws iam create-instance-profile --instance-profile-name $ROLE
    aws iam add-role-to-instance-profile --instance-profile-name $ROLE --role-name $ROLE
  fi
  aws iam put-role-policy --role-name $ROLE --policy-name s3-$BUCKET --policy-document \
    "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"s3:GetObject\",\"s3:PutObject\",\"s3:ListBucket\"],\"Resource\":[\"arn:aws:s3:::$BUCKET\",\"arn:aws:s3:::$BUCKET/*\"]}]}"
  aws s3 ls s3://$BUCKET/pairs/
  ;;
run)
  AMI=$(aws ec2 describe-images --region $REGION --owners amazon \
    --filters "Name=name,Values=Deep Learning OSS Nvidia Driver AMI GPU PyTorch*Ubuntu 22.04*" "Name=state,Values=available" \
    --query 'sort_by(Images,&CreationDate)[-1].[ImageId,Name]' --output text)
  echo "AMI: $AMI"
  UD=$(mktemp)
  sed -e "s/__BUCKET__/$BUCKET/g" -e "s/__MAX_HOURS__/$MAX_HOURS/g" ce/aws/ec2_user_data.sh > "$UD"
  aws ec2 run-instances --region $REGION --image-id "${AMI%%[[:space:]]*}" --instance-type $ITYPE --count 1 \
    --iam-instance-profile Name=$ROLE --instance-initiated-shutdown-behavior terminate \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":120,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
    --user-data "file://$UD" --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$TAG}]" \
    --query 'Instances[0].[InstanceId,State.Name]' --output text
  ;;
watch)
  while true; do
    ST=$(aws ec2 describe-instances --region $REGION --filters "Name=tag:Name,Values=$TAG" \
      "Name=instance-state-name,Values=pending,running,stopping,shutting-down" \
      --query 'Reservations[].Instances[].[InstanceId,State.Name,LaunchTime]' --output text)
    echo "=== $(date +%T) ${ST:-no live instance}"
    aws s3 cp s3://$BUCKET/logs/ce_job.log - 2>/dev/null | tr '\r' '\n' | grep -v "it/s\]" | tail -4 || true
    [ -z "$ST" ] && break
    sleep 300
  done
  ;;
fetch)
  aws s3 sync s3://$BUCKET/out/ work/ce/aws_out/
  aws s3 cp s3://$BUCKET/logs/ce_job.log work/ce/aws_out/ce_job.log
  find work/ce/aws_out -type f -exec ls -la {} \;
  ;;
*) echo "unknown step $STEP"; exit 2 ;;
esac
