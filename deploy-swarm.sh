#!/bin/bash

set -euo pipefail

STACK_NAME="${STACK_NAME:-md5-cracker}"
MANAGER_IMAGE="${MANAGER_IMAGE:-md5-cracker-manager:latest}"
WORKER_IMAGE="${WORKER_IMAGE:-md5-cracker-worker:latest}"

export DOCKER_CONTEXT=desktop-linux

SWARM_STATE=$(cmd.exe /c "docker info --format '{{.Swarm.LocalNodeState}}'" 2>/dev/null | tr -d '\r')
echo "Swarm state: $SWARM_STATE"

if [[ "$SWARM_STATE" != "'active'" ]]; then
  echo "Docker Swarm not initialized. Run: docker swarm init"
  exit 1
fi

cmd.exe /c "docker stack rm $STACK_NAME"
cmd.exe /c "docker network rm ${STACK_NAME}_md5-cracker-network" 2>nul || true
sleep 3

echo "Building images..."
cmd.exe /c "docker build -t $MANAGER_IMAGE ./manager"
cmd.exe /c "docker build -t $WORKER_IMAGE ./worker"

echo "Deploying stack..."
cmd.exe /c "docker stack deploy -c docker-stack.yml $STACK_NAME  --prune"

echo "Services:"
cmd.exe /c "docker stack services $STACK_NAME"