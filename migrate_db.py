import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
if DB_URL and DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DB_URL)

with engine.connect() as conn:
    print("Adding drift_threshold and bias_threshold to ai_systems...")
    try:
        conn.execute(text("ALTER TABLE ai_systems ADD COLUMN drift_threshold FLOAT"))
        print("drift_threshold added.")
    except Exception as e:
        print("drift_threshold might already exist:", str(e))
        
    try:
        conn.execute(text("ALTER TABLE ai_systems ADD COLUMN bias_threshold FLOAT"))
        print("bias_threshold added.")
    except Exception as e:
        print("bias_threshold might already exist:", str(e))
        
    conn.commit()
    print("Done!")
