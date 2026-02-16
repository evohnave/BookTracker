#!/usr/bin/env bash
set -euo pipefail

echo "Deleting Kubernetes resources..."
kubectl delete -f k8s/service.yaml --ignore-not-found
kubectl delete -f k8s/deployment.yaml --ignore-not-found
kubectl delete -f k8s/secret.yaml --ignore-not-found

echo "Done. Namespace 'booktracker' left intact."
