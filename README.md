# k8s-gitops-deployment

# Kubernetes GitOps Deployment with Observability

A production-style Kubernetes deployment for a FastAPI + PostgreSQL app — covering raw manifests, a parametrized Helm chart, GitOps automation with ArgoCD, and a full observability stack (Prometheus, Grafana, alerting, structured logging).

## Architecture
git push → ArgoCD (watches repo) → syncs Helm chart → Kubernetes cluster
│
┌───────────────────────────────┼───────────────────────┐
▼ ▼ ▼
task-api (3 replicas) postgres Prometheus (scrapes /metrics)
│ │
└── /metrics, /health ─────────────────────────► Grafana (dashboards) + Alertmanager


## Tech Stack
- **Kubernetes** (Docker Desktop) — orchestration
- **Helm** — templated, parametrized deployment
- **ArgoCD** — GitOps continuous deployment
- **Prometheus** — metrics collection
- **Grafana** — dashboards
- **Structured JSON logging** — application-level

## What This Demonstrates
- Progression from raw Kubernetes manifests to a parametrized Helm chart to a fully automated GitOps deployment
- Real GitOps behavior verified live: a `git push` (e.g. replica count change) triggers automatic cluster reconciliation with zero manual `kubectl`/`helm` commands
- Application-level observability: custom `/metrics` endpoint, Prometheus scraping via pod annotations, a 3-panel Grafana dashboard (request rate, p95 latency, error rate)
- Alerting on real conditions (high error rate, instance down)
- Structured JSON logging for meaningful business events, not just default access logs
- Recovering a fully GitOps-managed cluster from a genuine crash (see Incident Notes below) — proof that Git-as-source-of-truth isn't just a theoretical benefit

## How to Run Locally

**Prerequisites:** Docker Desktop with Kubernetes enabled, Helm, kubectl.

```bash
git clone https://github.com/<your-username>/k8s-gitops-deployment.git
cd k8s-gitops-deployment

# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml --server-side

# Deploy the app via ArgoCD
kubectl apply -f argocd/application.yaml

# Install Prometheus with alert rules
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/prometheus --namespace monitoring --create-namespace \
  --set server.persistentVolume.enabled=false --set alertmanager.persistentVolume.enabled=false \
  -f prometheus-alerts-values.yaml

# Install Grafana
helm repo add grafana https://grafana.github.io/helm-charts
helm install grafana grafana/grafana --namespace monitoring \
  --set persistence.enabled=false --set adminPassword=admin123
```

Access (each in a separate terminal):
```bash
kubectl port-forward svc/task-api 8000:8000
kubectl port-forward svc/argocd-server -n argocd 8080:443
kubectl port-forward svc/prometheus-server -n monitoring 9090:80
kubectl port-forward svc/grafana -n monitoring 3000:80
```

## GitOps in Action

Proven live: editing `charts/task-api/values.yaml` (e.g. `replicaCount: 2 → 3`), committing, and pushing causes ArgoCD to automatically detect the drift and scale the deployment — no `kubectl scale` or manual intervention.

## Observability

- **Dashboard**: Request Rate by Endpoint, p95 Latency by Endpoint, Error Rate (screenshot below)
- **Alerts**: `HighErrorRate` (>5% 5xx sustained 2min), `TaskApiDown` (instance unreachable 1min)
- **Logs**: structured JSON on business events (e.g. task creation), queryable by field

*(Add your dashboard screenshot here)*

## Design Decisions & Trade-offs

- **Helm + ArgoCD combo**: chosen for reusability (parametrized chart) plus automation (no manual deploys) — not universal practice, but a strong default for multi-environment apps. Raw-manifest or Kustomize + ArgoCD are equally valid for simpler cases.
- **Automated sync + self-heal enabled**: appropriate for a portfolio/dev context; a real production setup would likely require manual sync approval for prod environments specifically.
- **Secrets currently base64-encoded via Helm values, not encrypted**: a known limitation — production use would need Sealed Secrets or an external secrets manager (Azure Key Vault, AWS Secrets Manager).
- **Prometheus alert rules delivered via Helm values (`serverFiles.alerting_rules.yml`), not a separate ConfigMap**: initially attempted the `release: prometheus` label convention (used by `kube-prometheus-stack`/Prometheus Operator), which doesn't apply to the plain `prometheus-community/prometheus` chart used here — corrected after inspecting the config-reload sidecar's actual watched directory.
- **Prometheus/Grafana installed outside ArgoCD's management** (direct `helm install`, not GitOps-tracked): a known gap — bringing the full observability stack under GitOps too would be a natural next step.

## Incident Notes: Cluster Crash and Recovery

During development, simultaneous local resource pressure (ArgoCD + Prometheus + Grafana + app, all on a single-node Docker Desktop cluster) caused an `etcd` timeout that corrupted the cluster's internal state, requiring a full Kubernetes cluster reset. Because every component (ArgoCD, the Helm chart, application manifests) was defined declaratively in this Git repo, recovery was straightforward: reset the cluster, reinstall ArgoCD, reapply the `Application` resource, and the entire application stack resynced automatically from Git with no manual reconstruction. This is a direct, real demonstration of why Git-as-source-of-truth matters operationally, not just architecturally.

## What I'd Do Differently at Scale
- Bring Prometheus/Grafana under ArgoCD management too, for full GitOps coverage
- Use Sealed Secrets or an external secrets manager instead of Helm-values-based secrets
- Add a `PersistentVolumeClaim` for Postgres instead of `emptyDir` (data currently doesn't survive pod restarts)
- Require manual sync approval for a production environment, keep auto-sync for dev/staging only
- Add `postgres_exporter` for database-level metrics alongside the current application-level metrics

## Repo Structure


k8s-gitops-deployment/
├── app/ # FastAPI app (main.py, database.py, models.py, logging_config.py)
├── charts/task-api/ # Helm chart
│ ├── Chart.yaml
│ ├── values.yaml
│ └── templates/ # Deployment, Service, Secret manifests
├── k8s/base/ # Original raw manifests (kept for reference)
├── argocd/application.yaml # ArgoCD Application resource
├── prometheus-alerts-values.yaml # Prometheus alert rule config
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md


