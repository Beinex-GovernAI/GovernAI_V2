import requests
import time
import subprocess
import os
import sys

print("Starting FastAPI server...")
server_process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api.server:app", "--port", "8000"],
    cwd="governai"
)

try:
    # Wait for the server to boot up
    time.sleep(10)

    print("Testing /health endpoint...")
    resp = requests.get("http://localhost:8000/health")
    print(f"Health check status: {resp.status_code}")
    print(f"Response: {resp.json()}")

    print("\nTesting /api/v1/systems/register endpoint...")
    payload = {
        "name": "Customer Support Chatbot",
        "owner": "CX Team",
        "business_purpose": "We use this bot to classify incoming support tickets based on customer sentiment and urgency.",
        "model_type": "LLM",
        "model_vendor": "OpenAI",
        "model_source": "Proprietary",
        "drift_threshold": 0.15,
        "bias_threshold": 0.05
    }

    print("Sending payload:")
    print(payload)

    register_resp = requests.post("http://localhost:8000/api/v1/systems/register", json=payload)
    print(f"\nRegistration status: {register_resp.status_code}")
    print(f"Response: {register_resp.json()}")

    if register_resp.status_code == 200:
        system_id = register_resp.json()["system_id"]

        print(f"\nTesting /api/v1/systems/{system_id}/telemetry endpoint...")
        telemetry_payload = {
            "metrics": [
                {"name": "Drift", "value": 0.20}
            ]
        }
        print("Sending payload:")
        print(telemetry_payload)

        telemetry_resp = requests.post(
            f"http://localhost:8000/api/v1/systems/{system_id}/telemetry",
            json=telemetry_payload
        )
        print(f"\nTelemetry status: {telemetry_resp.status_code}")
        print(f"Response: {telemetry_resp.json()}")

        result = telemetry_resp.json()
        assert result["compliance_status"] == "Non-Compliant", "Expected status to flip to Non-Compliant after breach"
        assert result["metrics_ingested"][0]["is_breached"] is True, "Expected metric to be flagged as breached"
        print("\n[PASS] Golden Thread test passed: breach correctly flipped status to Non-Compliant.")
    else:
        print("\nSkipping telemetry test since registration failed.")

finally:
    print("\nShutting down FastAPI server...")
    server_process.terminate()
    server_process.wait()
    print("Server stopped.")