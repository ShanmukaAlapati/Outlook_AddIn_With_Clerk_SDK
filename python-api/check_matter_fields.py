"""
Diagnostic script: checks the actual DB state of matter_subtype_fields.
Run: python check_matter_fields.py
"""
import psycopg2, os, json
from dotenv import load_dotenv

load_dotenv()

def conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def run():
    c = conn()
    cur = c.cursor()

    print("=" * 60)
    print("1. matter_subtype_fields SCHEMA")
    print("=" * 60)
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'legal_saas' AND table_name = 'matter_subtype_fields'
        ORDER BY ordinal_position;
    """)
    for row in cur.fetchall():
        print(f"  {row[0]:30s}  type={row[1]:15s}  nullable={row[2]}  default={row[3]}")

    print("\n" + "=" * 60)
    print("2. UNIQUE CONSTRAINTS on matter_subtype_fields")
    print("=" * 60)
    cur.execute("""
        SELECT conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conrelid = 'legal_saas.matter_subtype_fields'::regclass;
    """)
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

    print("\n" + "=" * 60)
    print("3. matter_subtype_fields ROWS (all)")
    print("=" * 60)
    cur.execute("SELECT * FROM legal_saas.matter_subtype_fields;")
    rows = cur.fetchall()
    col_names = [desc[0] for desc in cur.description]
    print("  Columns:", col_names)
    if not rows:
        print("  *** NO ROWS FOUND — fields were never saved ***")
    for r in rows:
        print("  ", dict(zip(col_names, r)))

    print("\n" + "=" * 60)
    print("4. core_fields available")
    print("=" * 60)
    cur.execute("SELECT id, field_name, field_type FROM legal_saas.core_fields LIMIT 10;")
    for r in cur.fetchall():
        print(f"  id={r[0]}  name={r[1]}  type={r[2]}")

    print("\n" + "=" * 60)
    print("5. matter_subtypes")
    print("=" * 60)
    cur.execute("SELECT id, matter_type_id, name FROM legal_saas.matter_subtypes;")
    for r in cur.fetchall():
        print(f"  id={r[0]}  matter_type_id={r[1]}  name={r[2]}")

    print("\n" + "=" * 60)
    print("6. JOIN TEST (what GET endpoint returns)")
    print("=" * 60)
    cur.execute("""
        SELECT cf.id, cf.field_name, cf.field_type,
               COALESCE(msf.display_name, cf.display_name, cf.field_name),
               msf.display_order, msf.is_required,
               msf.core_field_id,
               COALESCE(msf.options, '[]'::jsonb)
        FROM legal_saas.core_fields cf
        JOIN legal_saas.matter_subtype_fields msf ON cf.id::text = msf.core_field_id
        LIMIT 20;
    """)
    rows = cur.fetchall()
    if not rows:
        print("  *** JOIN returns nothing — check core_field_id values vs core_fields.id ***")
    for r in rows:
        print(f"  cf.id={r[0]}  field={r[1]}  type={r[2]}  display={r[3]}  msf.core_field_id={r[6]}")

    cur.close()
    c.close()

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback; traceback.print_exc()
