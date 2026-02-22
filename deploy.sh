#!/usr/bin/env bash
set -euo pipefail

echo "Building Docker image..."
docker build -t booktracker:latest .

echo "Applying Kubernetes manifests..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

echo "Restarting deployment to pick up new image..."
kubectl rollout restart deployment booktracker -n booktracker
kubectl rollout status deployment booktracker -n booktracker

echo "Done. Visit http://localhost:30090/"
