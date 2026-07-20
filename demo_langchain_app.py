import requests
import json

# This is a mock LangChain app for the Resume Screening demo.
# Note: Since Grishma is implementing the generic scanner endpoint and internal analytics,
# we are simulating what this app will do once those endpoints are ready, and we will hit the existing 
# registration endpoint for now as a placeholder, printing the expected new behavior.

def simulate_resume_screening(resume_text: str):
    """
    Simulates a LangChain pipeline processing a resume.
    """
    print(f"\n[LangChain Agent] Processing resume...")
    # Simulated prediction
    if "Python" in resume_text and "AWS" in resume_text:
        decision = "Shortlisted"
        score = 0.85
    else:
        decision = "Rejected"
        score = 0.40
        
    print(f"[LangChain Agent] Decision: {decision} (Score: {score})")
    
    # 1. We prepare the payload for GovernAI generic scanner endpoint (to be built by Grishma)
    scanner_payload = {
        "system_metadata": {
            "name": "HR Resume Screener AI",
            "owner": "HR Dept",
            "business_purpose": "Automatically screens incoming resumes and ranks them based on job description fit.",
            "model_type": "LangChain Agent",
            "model_vendor": "OpenAI",
            "model_source": "Proprietary API",
        },
        "compliance_evidence": {
            "documentation_url": "https://wiki.beinex.com/hr-ai-screener"
        },
        "raw_prediction": {
            "input_text": resume_text,
            "output_text": decision,
            "confidence_score": score
        }
    }
    
    print("\n[GovernAI Intake] Sending raw data to GovernAI generic scanner endpoint...")
    print(json.dumps(scanner_payload, indent=2))
    
    try:
        resp = requests.post("http://localhost:8000/api/v1/scanner/intake", json=scanner_payload)
        
        if resp.status_code == 200:
            print(f"Successfully processed by GovernAI Intake! Response: {resp.json()}")
        else:
            print(f"Failed to process: {resp.text}")
    except Exception as e:
        print(f"Could not connect to GovernAI backend: {e}. Is the FastAPI server running?")

if __name__ == "__main__":
    sample_resume = "Experienced software engineer with 5 years in Python, AWS, and React."
    simulate_resume_screening(sample_resume)
