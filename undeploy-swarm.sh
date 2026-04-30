#!/bin/bash

set -euo pipefail

STACK_NAME="${STACK_NAME:-md5-cracker}"
REMOVE_VOLUMES="${REMOVE_VOLUMES:-0}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker не найден в PATH"
  exit 1
fi

if [[ "$(docker info --format '{{.Swarm.LocalNodeState}}')" != "active" ]]; then
  echo "Docker Swarm не активен"
  exit 1
fi

echo "Removing stack '$STACK_NAME'..."
docker stack rm "$STACK_NAME"

echo "Waiting for services to disappear..."
while docker stack services "$STACK_NAME" >/dev/null 2>&1; do
  sleep 2
done

if [[ "$REMOVE_VOLUMES" == "1" ]]; then
  echo "Removing local volumes..."
  docker volume rm \
    "${STACK_NAME}_mongodb_data" \
    "${STACK_NAME}_rabbitmq_data" >/dev/null 2>&1 || true
fi

echo "Undeploy complete"
