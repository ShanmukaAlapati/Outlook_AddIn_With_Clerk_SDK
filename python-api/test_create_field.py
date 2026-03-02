import psycopg2
import os
from dotenv import load_dotenv
import json

load_dotenv()

def test_create_field():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        
        org_id = "org_3ACS3qBXEOq9fxJocGcGGElM5Jx"
        name = "Test Field From Agent"
        ftype = "text"
        
        print(f"Creating field for org {org_id}...")
        cur.execute(
            """
            INSERT INTO legal_saas.field_definitions (org_id, name, type, config)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (org_id, name, ftype, json.dumps({}))
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        print(f"Created field with ID: {new_id}")
        
        cur.execute("SELECT org_id FROM legal_saas.field_definitions WHERE id = %s;", (new_id,))
        result = cur.fetchone()[0]
        print(f"Verified Org ID in DB: {result}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_create_field()
