import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def update_fields_org():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        
        org_id = "org_3ACS3qBXEOq9fxJocGcGGElM5Jx"
        
        print(f"Updating all field_definitions with NULL org_id to {org_id}...")
        cur.execute(
            """
            UPDATE legal_saas.field_definitions
            SET org_id = %s
            WHERE org_id IS NULL;
            """,
            (org_id,)
        )
        count = cur.rowcount
        conn.commit()
        print(f"Updated {count} fields.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_fields_org()
