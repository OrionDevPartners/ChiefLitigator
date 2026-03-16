#!/usr/bin/env bash
# =============================================================================
# Cyphergy — ECS Fargate Deployment Script
# Builds, pushes to ECR, updates ECS task definition and service.
# CPAA-compliant: reads all config from environment variables.
# SECURITY: Never logs secrets or credentials (@M:010).
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration (all from environment — CPAA)
# ---------------------------------------------------------------------------
AWS_REGION="${AWS_DEFAULT_REGION:?ERROR: AWS_DEFAULT_REGION is not set}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
ECR_REPO="cyphergy-api"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"
ECS_CLUSTER="${ECS_CLUSTER:-cyphergy-production}"
ECS_SERVICE="${ECS_SERVICE:-cyphergy-api}"
TASK_FAMILY="${TASK_FAMILY:-cyphergy-api}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

die() {
    log "FATAL: $*" >&2
    exit 1
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
log "=== Cyphergy Deployment ==="
log "Region:    ${AWS_REGION}"
log "ECR:       ${ECR_URI}"
log "Cluster:   ${ECS_CLUSTER}"
log "Service:   ${ECS_SERVICE}"
log "Tag:       ${IMAGE_TAG}"
log ""

# Verify required tools
for cmd in aws docker; do
    command -v "$cmd" >/dev/null 2>&1 || die "${cmd} is not installed"
done

# Verify AWS credentials are available (without printing them)
aws sts get-caller-identity >/dev/null 2>&1 || die "AWS credentials are invalid or not configured"
log "AWS credentials verified"

# ---------------------------------------------------------------------------
# Step 1: Build Docker image
# ---------------------------------------------------------------------------
log "Step 1/5: Building Docker image..."
docker build \
    --platform linux/amd64 \
    --tag "${ECR_REPO}:${IMAGE_TAG}" \
    --tag "${ECR_REPO}:latest" \
    --file Dockerfile \
    .
log "Build complete: ${ECR_REPO}:${IMAGE_TAG}"

# ---------------------------------------------------------------------------
# Step 2: Authenticate and push to ECR
# ---------------------------------------------------------------------------
log "Step 2/5: Pushing to ECR..."
aws ecr get-login-password --region "${AWS_REGION}" \
    | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker tag "${ECR_REPO}:${IMAGE_TAG}" "${ECR_URI}:${IMAGE_TAG}"
docker tag "${ECR_REPO}:latest" "${ECR_URI}:latest"
docker push "${ECR_URI}:${IMAGE_TAG}"
docker push "${ECR_URI}:latest"
log "Pushed: ${ECR_URI}:${IMAGE_TAG}"

# ---------------------------------------------------------------------------
# Step 3: Update ECS task definition with new image
# ---------------------------------------------------------------------------
log "Step 3/5: Updating task definition..."

# Get the current task definition
CURRENT_TASK_DEF=$(aws ecs describe-task-definition \
    --task-definition "${TASK_FAMILY}" \
    --region "${AWS_REGION}" \
    --query 'taskDefinition' \
    --output json)

# Build new task definition with updated image
NEW_TASK_DEF=$(echo "${CURRENT_TASK_DEF}" | python3 -c "
import sys, json
task_def = json.load(sys.stdin)
# Update the container image
for container in task_def['containerDefinitions']:
    if container['name'] == 'cyphergy-api':
        container['image'] = '${ECR_URI}:${IMAGE_TAG}'
# Remove fields that cannot be included in register-task-definition
for field in ['taskDefinitionArn', 'revision', 'status', 'requiresAttributes',
              'compatibilities', 'registeredAt', 'registeredBy']:
    task_def.pop(field, None)
print(json.dumps(task_def))
")

# Register the new task definition
NEW_TASK_ARN=$(echo "${NEW_TASK_DEF}" | aws ecs register-task-definition \
    --region "${AWS_REGION}" \
    --cli-input-json file:///dev/stdin \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

log "Registered: ${NEW_TASK_ARN}"

# ---------------------------------------------------------------------------
# Step 4: Update ECS service to use new task definition
# ---------------------------------------------------------------------------
log "Step 4/5: Updating ECS service..."
aws ecs update-service \
    --region "${AWS_REGION}" \
    --cluster "${ECS_CLUSTER}" \
    --service "${ECS_SERVICE}" \
    --task-definition "${NEW_TASK_ARN}" \
    --force-new-deployment \
    --query 'service.serviceName' \
    --output text >/dev/null

log "Service update initiated"

# ---------------------------------------------------------------------------
# Step 5: Wait for deployment to stabilize
# ---------------------------------------------------------------------------
log "Step 5/5: Waiting for deployment to stabilize..."
log "(This may take 2-5 minutes)"

if aws ecs wait services-stable \
    --region "${AWS_REGION}" \
    --cluster "${ECS_CLUSTER}" \
    --services "${ECS_SERVICE}" 2>/dev/null; then
    log "=== Deployment successful ==="
    log "Image: ${ECR_URI}:${IMAGE_TAG}"
    log "Task:  ${NEW_TASK_ARN}"
else
    log "WARNING: Service did not stabilize within timeout"
    log "Check the ECS console for deployment status:"
    log "  https://${AWS_REGION}.console.aws.amazon.com/ecs/v2/clusters/${ECS_CLUSTER}/services/${ECS_SERVICE}"
    exit 1
fi
