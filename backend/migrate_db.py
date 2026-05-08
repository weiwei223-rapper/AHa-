import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
engine = create_engine(url)

columns = [
    ("starter_code", "TEXT"),
    ("test_cases_json", "TEXT"),
    ("explanation", "TEXT"),
    ("reference_concept", "TEXT"),
    ("source_time", "TEXT"),
    ("source_excerpt", "TEXT")
]

with engine.connect() as conn:
    for col_name, col_type in columns:
        try:
            print(f"Adding column {col_name}...")
            conn.execute(text(f"ALTER TABLE quiz_questions ADD COLUMN {col_name} {col_type}"))
            conn.commit()
            print(f"Column {col_name} added successfully.")
        except Exception as e:
            print(f"Could not add column {col_name} (it might already exist): {e}")
            conn.rollback()
