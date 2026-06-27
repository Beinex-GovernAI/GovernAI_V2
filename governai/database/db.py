import os
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from dotenv import load_dotenv

# Load environment variables from .env if it exists
load_dotenv()

# Ensure DATABASE_URL is set, or provide their Supabase connection string as the default
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql+psycopg://postgres:[YOUR-PASSWORD]@db.agoxhxzxabuyibkmwite.supabase.co:5432/postgres"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_uuid():
    return str(uuid.uuid4())
