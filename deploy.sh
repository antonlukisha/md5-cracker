#!/bin/bash

@echo off
echo Loading images...
minikube image load md5-cracker-manager:latest
minikube image load md5-cracker-worker:latest

echo Deploying...
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/mongodb/
kubectl apply -f k8s/rabbitmq/
kubectl apply -f k8s/manager/
kubectl apply -f k8s/worker/

echo Waiting 30 seconds...
timeout /t 30

echo Done!
kubectl get pods -n md5-cracker