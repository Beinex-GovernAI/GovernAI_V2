import sys
import os
# Add the governai folder to the Python path so it can resolve database/services modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import SessionLocal, engine, Base
from database.models import AISystem, DataSource
from services.ai_system_svc import create_system, add_data_source
from services.audit_svc import log_action

def seed_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if already seeded
    if db.query(AISystem).first():
        print("Database already seeded. Skipping...")
        db.close()
        return

    admin_user = "Admin"
    
    print("Seeding sample systems...")
    
    # 1. Resume Screening AI
    sys1 = create_system(db, {
        "name": "Resume Screening AI",
        "owner": "HR Department",
        "business_purpose": "Automated initial screening of job applicants.",
        "model_vendor": "OpenAI",
        "model_type": "LLM",
        "model_source": "Proprietary",
        "agentic_trace_required": "No"
    }, admin_user)
    
    add_data_source(db, sys1.id, {
        "source_name": "Workday ATS",
        "description": "Applicant resumes and profile data.",
        "contains_pii": 1,
        "pii_categories": "Names, Emails, Employment History, Education"
    }, admin_user)

    # 2. Loan Approval AI
    sys2 = create_system(db, {
        "name": "Loan Approval AI",
        "owner": "Risk Operations",
        "business_purpose": "Automated credit risk assessment.",
        "model_vendor": "In-house",
        "model_type": "Classical ML",
        "model_source": "Open Source",
        "agentic_trace_required": "No"
    }, admin_user)

    add_data_source(db, sys2.id, {
        "source_name": "Core Banking System",
        "description": "Customer financial history and credit scores.",
        "contains_pii": 1,
        "pii_categories": "Financial Data, SSN, Names, Addresses"
    }, admin_user)

    # 3. Customer Support Assistant
    sys3 = create_system(db, {
        "name": "Customer Support Assistant",
        "owner": "Customer Success",
        "business_purpose": "Chatbot for answering common FAQs.",
        "model_vendor": "Anthropic",
        "model_type": "LLM",
        "model_source": "Proprietary",
        "agentic_trace_required": "No"
    }, admin_user)

    add_data_source(db, sys3.id, {
        "source_name": "Zendesk KB",
        "description": "Public knowledge base articles.",
        "contains_pii": 0,
        "pii_categories": ""
    }, admin_user)

    # 4. Meeting Scheduling Agent
    sys4 = create_system(db, {
        "name": "Meeting Scheduling Agent",
        "owner": "Internal IT",
        "business_purpose": "Autonomous agent for finding calendar slots.",
        "model_vendor": "Microsoft",
        "model_type": "Agentic AI",
        "model_source": "Proprietary",
        "agentic_trace_required": "Yes"
    }, admin_user)

    add_data_source(db, sys4.id, {
        "source_name": "Exchange Calendar",
        "description": "Employee availability and meeting titles.",
        "contains_pii": 1,
        "pii_categories": "Names, Email Addresses"
    }, admin_user)
    
    print("Database seeded successfully.")
    db.close()

if __name__ == "__main__":
    seed_db()
