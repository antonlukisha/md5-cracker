#!/bin/bash

set -euo pipefail

NAMESPACE="${NAMESPACE:-md5-cracker}"
KUBE_CONTEXT="${KUBE_CONTEXT:-$(kubectl config current-context)}"
SKIP_MONITORING="${SKIP_MONITORING:-0}"
SKIP_IMAGE_BUILD="${SKIP_IMAGE_BUILD:-0}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
MANAGER_IMAGE="${MANAGER_IMAGE:-md5-cracker-manager:${IMAGE_TAG}}"
WORKER_IMAGE="${WORKER_IMAGE:-md5-cracker-worker:${IMAGE_TAG}}"
MANAGER_CONTAINER_NAME="${MANAGER_CONTAINER_NAME:-manager}"
WORKER_CONTAINER_NAME="${WORKER_CONTAINER_NAME:-worker}"

kubectl_ctx() {
  kubectl --context "$KUBE_CONTEXT" "$@"
}

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl not found in PATH"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found in PATH"
  exit 1
fi

HELM_BIN="${HELM_BIN:-helm}"
if ! command -v "$HELM_BIN" >/dev/null 2>&1; then
  if command -v helm.exe >/dev/null 2>&1; then
    HELM_BIN="helm.exe"
  elif [[ -x "/c/Program Files/Helm/helm.exe" ]]; then
    HELM_BIN="/c/Program Files/Helm/helm.exe"
  elif [[ -x "/c/Program Files/Helm/windows-amd64/helm.exe" ]]; then
    HELM_BIN="/c/Program Files/Helm/windows-amd64/helm.exe"
  fi
fi

echo "Kubernetes context: $KUBE_CONTEXT"

build_images() {
  echo "Building local images..."
  docker build -t "$MANAGER_IMAGE" "./manager"
  docker build -t "$WORKER_IMAGE" "./worker"
}

load_images() {
  case "$KUBE_CONTEXT" in
    minikube)
      echo "Loading images into minikube..."
      minikube image load "$MANAGER_IMAGE"
      minikube image load "$WORKER_IMAGE"
      ;;
    docker-desktop)
      echo "docker-desktop shares the local Docker image store, skipping image load"
      ;;
    *)
      echo "Unknown context '$KUBE_CONTEXT'; assuming cluster can access local images directly"
      ;;
  esac
}

wait_for_mongodb() {
  echo "Waiting for MongoDB pods to be ready..."
  kubectl_ctx rollout status statefulset/mongodb -n "$NAMESPACE" --timeout=600s
}

init_mongodb_replicaset() {
  echo "Initializing MongoDB replica set..."
  kubectl_ctx delete job mongodb-init-replicaset -n "$NAMESPACE" --ignore-not-found=true
  kubectl_ctx apply -f k8s/mongodb/init-replicaset-job.yaml
  kubectl_ctx wait --for=condition=complete job/mongodb-init-replicaset -n "$NAMESPACE" --timeout=300s
}

deploy_monitoring() {
  if [[ "$SKIP_MONITORING" == "1" ]]; then
    echo "Skipping Prometheus/Grafana installation (SKIP_MONITORING=1)"
    return
  fi

  if ! command -v "$HELM_BIN" >/dev/null 2>&1; then
    echo "helm not found in PATH. Do you have installed Helm or run: SKIP_MONITORING=1 bash ./deploy.sh"
    exit 1
  fi

  echo "Installing or upgrading Prometheus/Grafana..."
  "$HELM_BIN" repo add prometheus-community https://prometheus-community.github.io/helm-charts || true
  "$HELM_BIN" repo update

  if "$HELM_BIN" status prometheus-stack -n monitoring >/dev/null 2>&1; then
    "$HELM_BIN" upgrade prometheus-stack prometheus-community/kube-prometheus-stack \
      --namespace monitoring \
      --set grafana.enabled=true \
      --set grafana.sidecar.dashboards.enabled=true \
      --set grafana.sidecar.dashboards.label=grafana_dashboard \
      --set-string grafana.sidecar.dashboards.labelValue=1 \
      --set grafana.sidecar.dashboards.searchNamespace=ALL
  else
    "$HELM_BIN" install prometheus-stack prometheus-community/kube-prometheus-stack \
      --namespace monitoring \
      --create-namespace \
      --set grafana.enabled=true \
      --set grafana.sidecar.dashboards.enabled=true \
      --set grafana.sidecar.dashboards.label=grafana_dashboard \
      --set-string grafana.sidecar.dashboards.labelValue=1 \
      --set grafana.sidecar.dashboards.searchNamespace=ALL
  fi
}

if [[ "$SKIP_IMAGE_BUILD" != "1" ]]; then
  build_images
fi

load_images
kubectl_ctx apply -f k8s/namespace.yaml
deploy_monitoring

kubectl_ctx apply -f k8s/mongodb/
wait_for_mongodb
init_mongodb_replicaset
kubectl_ctx apply -f k8s/rabbitmq/
kubectl_ctx rollout status statefulset/rabbitmq -n "$NAMESPACE" --timeout=600s
kubectl_ctx apply -f k8s/manager/
kubectl_ctx apply -f k8s/worker/
kubectl_ctx rollout status deployment/manager -n "$NAMESPACE" --timeout=600s
kubectl_ctx rollout status deployment/worker -n "$NAMESPACE" --timeout=600s

if [[ "$SKIP_MONITORING" != "1" ]]; then
  kubectl_ctx apply -f k8s/grafana-dashboards.yaml
fi

echo "Deployment complete"
kubectl_ctx get pods -n "$NAMESPACE"