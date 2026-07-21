import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'governai'))

from database.db import SessionLocal  # adjust import if your db.py names it differently
from database.models import AISystem

db = SessionLocal()
system = db.query(AISystem).filter(AISystem.name == "HR Resume Screener AI").first()

if system:
    print(f"ID:         {system.id}")
    print(f"Updated at: {system.updated_at}")
else:
    print("System not found")

db.close()