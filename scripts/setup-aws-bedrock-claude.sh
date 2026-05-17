#!/usr/bin/env bash
set -euo pipefail

PROFILE="${AWS_PROFILE:-default}"
REGION="${AWS_REGION:-us-east-1}"

echo "AWS profile: ${PROFILE}"
echo "AWS region:  ${REGION}"

if ! command -v aws >/dev/null 2>&1; then
  echo "AWS CLI not found. Install it first: brew install awscli" >&2
  exit 1
fi

echo "AWS CLI: $(aws --version)"

if ! aws sts get-caller-identity --profile "${PROFILE}" >/dev/null 2>&1; then
  echo "No usable AWS profile named '${PROFILE}'."
  echo "Choose one setup path:"
  echo "  aws configure sso --profile ${PROFILE}"
  echo "  aws sso login --profile ${PROFILE}"
  echo "or:"
  echo "  aws configure --profile ${PROFILE}"
  exit 2
fi

echo "AWS identity:"
aws sts get-caller-identity --profile "${PROFILE}"

echo "Opening Bedrock Anthropic model catalog..."
open "https://${REGION}.console.aws.amazon.com/bedrock/home?region=${REGION}#/model-catalog?search=Anthropic" >/dev/null 2>&1 || true

echo
echo "In the browser:"
echo "1. Open each Anthropic Claude model you want."
echo "2. Click Request access / Enable access."
echo "3. Submit the use-case form."
echo "4. Wait until access is granted."
echo

echo "Anthropic foundation models visible in ${REGION}:"
aws bedrock list-foundation-models \
  --region "${REGION}" \
  --profile "${PROFILE}" \
  --by-provider Anthropic \
  --query 'modelSummaries[].{id:modelId,name:modelName,modalities:outputModalities}' \
  --output table || true

echo
echo "Inference profiles visible in ${REGION}:"
aws bedrock list-inference-profiles \
  --region "${REGION}" \
  --profile "${PROFILE}" \
  --query 'inferenceProfileSummaries[?contains(inferenceProfileId, `anthropic`)].{id:inferenceProfileId,name:inferenceProfileName,status:status}' \
  --output table || true

echo
echo "Next: run OpenCode with:"
echo "  AWS_PROFILE=${PROFILE} AWS_REGION=${REGION} opencode"
echo
echo "Next: run Claude Code with:"
echo "  CLAUDE_CODE_USE_BEDROCK=1 AWS_PROFILE=${PROFILE} AWS_REGION=${REGION} claude"
