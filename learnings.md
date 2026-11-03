# WeeBit: Architectural & Infrastructure Post-Mortem

This file documents project insights, hurdles and lessons learned in building and deploying a complete web application.  

WeeBit is a deterministic link shortening web application consisting of a: 
 - Backend web API written in Python 3.11 with FastAPI leveraging:
   - SQLAlchemy ORM modelling a simple data [model](backend/src/weebit/modules/links/models.py). 
   - Pydantic validation of HTTP request and response [DTOs](backend/src/weebit/modules/links/schemas.py).
 - Frontend reactive web application framed in React/NextJS and written in TypeScript. 
   - ASDS











## 1. System Design & Service Interoperability

### Graceful Degradation & Resilience Patterns
- **Fail-Open Component Design:** Secondary infrastructure (e.g., Redis caching layer, visitor analytics logging) must never sit directly on critical request paths without fault isolation. Wrapping non-critical dependencies in decorator-based resilience wrappers (`FailOpenCache`) and short socket timeouts (`socket_timeout=0.25`) ensures transient cache or telemetry failures never degrade core HTTP operations or return 500-level errors to users.
- **Fail-Closed Hard Dependencies:** Primary datastores (PostgreSQL) are fundamental system requirements. Instead of letting database driver drops bubble up as uncaught exceptions, explicit application-level error handlers and 503 `Service Unavailable` circuit breakers should be enforced when database connection pools are exhausted or unreachable.

---

## 2. Infrastructure as Code & Cloud Orchestration (Terraform & Azure)

### PaaS Specification Alignment vs. Iterative Guesswork
- **Azure/Oryx Build Automation Nuances:** Azure App Service enforces strict, opinionated build patterns (e.g., remote `antenv` construction using Kudu and Oryx). Attempting to deploy raw local environments or generic zip bundles without supplying expected build artifacts (`requirements.txt` exported via `uv`) leads to missing runtime binaries like `uvicorn`.
- **Deployment Mechanism Selection:** Using low-level upload commands (`az webapp deploy`) bypasses server-side dependency installation. Utilizing deployment sources optimized for zip deployment (`az webapp deployment source config-zip`) ensures remote build hooks execute reliably.
- **Cost of Distant Feedback Loops:** Relying on full cloud redeployments to test minor environment binding changes introduces severe time penalties due to Azure container cold-start latency. Local emulation and strict environment contract definition must take priority over remote trial-and-error.

---

## 3. Security, Configuration & Secret Management

### Operational Security & Exposure Risks
- **Diagnostic Endpoint Sanitization:** Public `/diagnostics` or health check endpoints must purely evaluate connectivity status (e.g., `"status": "ok"`) and latency metrics (`latency_ms`). They should never dump raw environment variables, connection strings, or underlying driver DSNs.
- **Incident Response & Secret Containment:** Unintentionally exposing connection strings containing embedded credentials (e.g., Key Vault secrets or database DSNs) highlights the necessity of a pre-planned incident response protocol. While resource group teardown and purge-deleting Key Vault instances (`az keyvault purge`) mitigates immediate exposure, automated secret rotation mechanisms provide cleaner, low-downtime containment.

---

## 4. Observability & Debugging

### Structured Telemetry over Introspection
- **Centralized Application Logging:** Exposing system state via public endpoints to debug configuration bindings is a security hazard borne out of missing telemetry. Implementing standard Python structured logging (`logging.getLogger(__name__)`) combined with Azure App Service log streaming (`az webapp log tail`) provides real-time visibility into TLS handshakes and driver exceptions without raw data leaks.
- **Proactive Health Probing:** Standardized `/health/database` and `/health/cache` probes should evaluate internal read/write operations within strict time budgets (e.g., `asyncio.wait_for(..., timeout=0.5)`) to detect degraded state before it impacts end users.

---

## 5. Development Workflow & Automation

### Orchestration with `Justfile` & Local Parity
- **Unified Local vs. Production Workflows:** Using `just` recipes guarantees repeatable build and deployment pipelines locally and in CI/CD.
- **Build Artifact Isolation:** Automating clean-up routines prior to packaging (e.g., stripping `__pycache__`, generating headless `requirements.txt` manifests via `uv export`) prevents local environment artifacts from contaminating remote Linux container runtimes.
