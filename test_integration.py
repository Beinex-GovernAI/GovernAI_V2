import requests
import time
import subprocess
import os

print("Starting FastAPI server...")
server_process = subprocess.Popen(
    ["uvicorn", "api.server:app", "--port", "8000"],
    cwd="governai"
)

try:
    # Wait for the server to boot up
    time.sleep(3)
    
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

finally:
    print("\nShutting down FastAPI server...")
    server_process.terminate()
    server_process.wait()
    print("Server stopped.")
