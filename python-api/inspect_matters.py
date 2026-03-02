import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        port=os.getenv("DB_PORT", "5432")
    )

def inspect_table():
    conn = get_db_connection()
    cur = conn.cursor()
    
    for table in ['matters', 'matter_assignees']:
        cur.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'legal_saas' AND table_name = '{table}'
            ORDER BY ordinal_position;
        """)
        
        columns = cur.fetchall()
        print(f"\nTable: legal_saas.{table}")
        for col in columns:
            print(f"Column: {col[0]}, Type: {col[1]}, Nullable: {col[2]}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    try:
        inspect_table()
    except Exception as e:
        print(f"Error: {e}")
