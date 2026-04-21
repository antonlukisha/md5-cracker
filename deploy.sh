#!/bin/bash

export PATH=$PATH:"/c/Program Files/Helm/windows-amd64"

if ! command -v helm &> /dev/null; then
    echo "Helm не найден! Убедитесь, что путь правильный"
    exit 1
fi

kubectl apply -f k8s/namespace.yaml

echo "Установка Prometheus и Grafana..."

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.enabled=true \
  --set grafana.sidecar.dashboards.enabled=true \
  --set grafana.sidecar.dashboards.label=grafana_dashboard \
  --set grafana.sidecar.dashboards.labelValue="1" \
  --set grafana.sidecar.dashboards.searchNamespace=ALL

kubectl apply -f k8s/mongodb/

kubectl apply -f k8s/rabbitmq/

kubectl apply -f k8s/manager/

kubectl apply -f k8s/worker/

kubectl apply -f k8s/grafana-dashboards.yaml

echo "Waiting for MongoDB to be ready..."
kubectl wait --for=condition=ready pod -l app=mongodb -n md5-cracker --timeout=300s

echo "Deployment complete"
