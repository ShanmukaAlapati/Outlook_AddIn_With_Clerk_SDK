import psycopg2
import os
from dotenv import load_dotenv

# Import the schema creation functions from db_func
from db_func import ensure_schema, ensure_matter_settings_schema, get_db_connection

load_dotenv()

def recreate_schema():
    print("Warning: This will drop the existing 'legal_saas' schema and all its data in the new database.")
    
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        print("Dropping existing schema...")
        cur.execute("DROP SCHEMA IF EXISTS legal_saas CASCADE;")
        
        print("Recreating schema from db_func.py definitions...")
        ensure_schema()
        
        print("Recreating matter settings schema...")
        # Since ensure_schema already calls ensure_matter_settings_schema, we might not need to call it again, 
        # but calling it is safe.
        ensure_matter_settings_schema()
        
        print("Schema recreation completed successfully. All constraints and indexes should now be present.")
        print("NOTE: You will need to re-run your data migration script to populate the tables.")
        
    except Exception as e:
        print(f"Error during schema recreation: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    recreate_schema()
