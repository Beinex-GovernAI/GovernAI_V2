from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="GovernAI Integration API",
    description="API for integrating real AI systems with GovernAI for automated risk assessment and telemetry tracking.",
    version="1.0.0"
)

# Allow all origins for the presentation phase
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "GovernAI Integration API is running"}

# Endpoints for System Registration and Telemetry will be added here
