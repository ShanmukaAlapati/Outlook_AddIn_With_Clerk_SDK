import os
import csv
from dotenv import load_dotenv
from db_func import get_db_connection, ensure_schema

load_dotenv()

def migrate_core_fields(csv_path: str):
    """
    Reads the CSV and inserts the core fields into the database schema.
    """
    print("Ensuring DB schema for core fields exists...")
    ensure_schema()
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        with open(csv_path, 'r', encoding='latin-1') as f:
            # Skip 2 non-data header lines (description row + empty row)
            next(f)
            next(f)
            reader = csv.DictReader(f)
            
            # Map of column names based on the CSV structure
            field_name_col = 'Field Name'
            field_type_col = 'Type of Field'
            is_core_col = 'Core Platform Field'
            comments_col = 'Comments'
            
            added_count = 0
            
            for row in reader:
                field_name = row.get(field_name_col, '').strip()
                field_type = row.get(field_type_col, '').strip()
                
                # Check for skipped rows (like empty ones)
                if not field_name or field_name == 'Field Name':
                    continue
                
                is_core = True  # We assume all from the core CSV are core fields
                comments = row.get(comments_col, '').strip()

                cur.execute(
                    """
                    INSERT INTO legal_saas.core_fields (field_name, field_type, is_core, comments)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (field_name, field_type, is_core, comments)
                )
                added_count += 1
                
        conn.commit()
        print(f"Successfully migrated {added_count} core fields.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error migrating core fields: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    csv_file = os.path.join(os.path.dirname(__file__), '..', 'Core FieldsSheet1.csv')
    migrate_core_fields(csv_file)
