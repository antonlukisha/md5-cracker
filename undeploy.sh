#!/bin/bash

kubectl delete -f k8s/grafana-dashboards.yaml
kubectl delete -f k8s/worker/
kubectl delete -f k8s/manager/
kubectl delete -f k8s/rabbitmq/
kubectl delete -f k8s/mongodb/
kubectl delete -f k8s/namespace.yaml

echo "Shutdown complete"
