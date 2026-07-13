# Telemetry & Golden Thread Integration Task

Hello! You are assisting Grishma with her tasks for the GovernAI project. Your goal is to implement the real-time telemetry webhook and the "Golden Thread" compliance logic. 

## Context
GovernAI is an AI governance platform. We just added a FastAPI integration layer (found in `governai/api/`) alongside the main Streamlit application. 

Abhay is currently working on the system registration endpoint (`POST /api/v1/systems/register`). 
Your task is to implement the telemetry endpoint: `POST /api/v1/systems/{system_id}/telemetry`

## Database Schema & Pydantic
We use SQLAlchemy for the database (see `governai/database/models.py`). 
We use Pydantic for the FastAPI request bodies (see `governai/api/schemas.py`). 

## Your Objectives

### 1. Update Registration Schema (Telemetry Thresholds)
In `governai/api/schemas.py`, `SystemRegistrationRequest` already includes `drift_threshold` and `bias_threshold`. Ensure that the `TelemetryPayload` and `TelemetryMetric` schemas are fully set up to accept incoming arrays of metrics (e.g. `[{"name": "Drift", "value": 0.15}]`).

### 2. Implement the Telemetry Endpoint
In `governai/api/server.py`, add the `POST /api/v1/systems/{system_id}/telemetry` route.

When this endpoint is hit by an external AI system, it must:
1. Fetch the `AISystem` from the database using the `system_id`.
2. Save each incoming metric to the `monitoring_metrics` table (`governai/database/models.py`).
3. **The Golden Thread Logic**: Compare the incoming metric's `value` against the threshold saved in the `AISystem` profile (e.g., if it's a Drift metric, compare it against the system's `drift_threshold`, though you may need to add these threshold columns to the `AISystem` model if they don't exist yet, or store them in a configuration JSON field!). 
4. If a threshold is breached, the endpoint must automatically:
   - Change the `AISystem.compliance_status` to `"At Risk"`.
   - Write an immutable record to the `audit_logs` table with `action="METRIC_BREACH"`.

## Branching Strategy
1. Create a new branch: `git checkout -b grishma/telemetry-engine`
2. Implement your changes.
3. Test by running the FastAPI server locally (`uvicorn governai.api.server:app --reload`).
4. Commit and push your branch to GitHub.
