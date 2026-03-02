import psycopg2
import os
from dotenv import load_dotenv
import json

load_dotenv()

def check_db():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        
        print("Checking field_definitions table...")
        cur.execute("SELECT * FROM legal_saas.field_definitions;")
        rows = cur.fetchall()
        print(f"Total field definitions: {len(rows)}")
        for r in rows:
            print(f"ID: {r[0]}, Org: {r[1]}, Name: {r[2]}, Type: {r[3]}")
            
        print("\nChecking matter_types table...")
        cur.execute("SELECT * FROM legal_saas.matter_types;")
        rows = cur.fetchall()
        print(f"Total matter types: {len(rows)}")
        for r in rows:
            print(f"ID: {r[0]}, Org: {r[1]}, Name: {r[2]}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
