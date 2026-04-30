#!/bin/bash

set -euo pipefail

NAMESPACE="${NAMESPACE:-md5-cracker}"
KUBE_CONTEXT="${KUBE_CONTEXT:-$(kubectl config current-context)}"

kubectl_ctx() {
  kubectl --context "$KUBE_CONTEXT" "$@"
}

kubectl_ctx delete -f k8s/grafana-dashboards.yaml --ignore-not-found=true || true
kubectl_ctx delete -f k8s/worker/ --ignore-not-found=true || true
kubectl_ctx delete -f k8s/manager/ --ignore-not-found=true || true
kubectl_ctx delete -f k8s/rabbitmq/ --ignore-not-found=true || true
kubectl_ctx delete -f k8s/mongodb/ --ignore-not-found=true || true
kubectl_ctx delete namespace "$NAMESPACE" --ignore-not-found=true || true

echo "Shutdown complete for context: $KUBE_CONTEXT"
