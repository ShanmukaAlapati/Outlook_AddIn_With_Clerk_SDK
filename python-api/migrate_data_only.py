import psycopg2
from psycopg2.extras import execute_values
from psycopg2.extensions import AsIs
import os
import json
from dotenv import load_dotenv

load_dotenv()

OLD_DB_URL = "postgresql://case_counsel_user:Rpo5MURxme2Nx8wRLE70JOHORvfu4F3A@dpg-d6aqqmvpm1nc73dhfg4g-a.oregon-postgres.render.com/case_counsel"
NEW_DB_URL = os.getenv("DATABASE_URL")

SCHEMA = "legal_saas"

def migrate_data():
    if not NEW_DB_URL:
        print("DATABASE_URL not found!")
        return

    old_conn = psycopg2.connect(OLD_DB_URL)
    new_conn = psycopg2.connect(NEW_DB_URL)
    
    old_cur = old_conn.cursor()
    new_cur = new_conn.cursor()

    old_cur.execute(f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{SCHEMA}';")
    tables = [t[0] for t in old_cur.fetchall()]

    print("Starting data migration...")
    
    for table_name in tables:
        print(f"Migrating table {SCHEMA}.{table_name}...")
        
        # Get column names
        old_cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = '{SCHEMA}' AND table_name = '{table_name}' ORDER BY ordinal_position;")
        cols = old_cur.fetchall()
        col_names = [c[0] for c in cols]
        
        old_cur.execute(f'SELECT {",".join(col_names)} FROM {SCHEMA}.{table_name}')
        rows = old_cur.fetchall()
        
        if not rows:
            print(f"  No rows to migrate.")
            continue
            
        print(f"  Fetching {len(rows)} rows...")
        
        # We need to adapt dicts to JSON literals for psycopg2
        adapted_rows = []
        for row in rows:
            adapted_row = []
            for val in row:
                if isinstance(val, dict) or isinstance(val, list):
                    # psycopg2 execute_values doesn't handle dicts cleanly without json wrapper
                    adapted_row.append(json.dumps(val))
                else:
                    adapted_row.append(val)
            adapted_rows.append(tuple(adapted_row))

        # Insert into new DB
        insert_query = f"INSERT INTO {SCHEMA}.{table_name} ({','.join(col_names)}) VALUES %s"
        try:
            execute_values(new_cur, insert_query, adapted_rows)
            new_conn.commit()
            print(f"  ✓ Inserted {len(rows)} rows.")
        except Exception as e:
            new_conn.rollback()
            print(f"  ✗ Failed to migrate {table_name}: {e}")

    # Fix Sequences
    print("Fixing sequences...")
    for table_name in tables_to_migrate:
        # Check if table has an 'id' column
        new_cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_schema = '{SCHEMA}' AND table_name = '{table_name}' AND column_name = 'id';")
        if new_cur.fetchone():
            seq_name = f"{table_name}_id_seq"
            # Check if sequence exists
            new_cur.execute(f"SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = '{SCHEMA}' AND sequence_name = '{seq_name}';")
            if new_cur.fetchone():
                try:
                    new_cur.execute(f"SELECT setval('{SCHEMA}.{seq_name}', COALESCE((SELECT MAX(id) FROM {SCHEMA}.{table_name}), 1), true);")
                    new_conn.commit()
                    print(f"  ✓ Set sequence {seq_name}")
                except Exception as e:
                    new_conn.rollback()
                    print(f"  ✗ Failed to set sequence {seq_name}: {e}")

    old_cur.close()
    old_conn.close()
    new_cur.close()
    new_conn.close()
    print("Data migration completed!")

if __name__ == "__main__":
    migrate_data()
