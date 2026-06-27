import sys
import os
# Add the governai folder to the Python path so it can resolve database/services modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import engine, Base
# Import all models to ensure they are registered with Base before creating tables
from database.models import (
    AISystem, DataSource, RiskAssessment, RiskClassificationAnswer,
    ComplianceRecord, MonitoringMetric, AuditLog, AgentActionTrace
)

def init_db():
    print("Creating database tables if they do not exist...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    init_db()
