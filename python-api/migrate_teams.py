"""
Migration script to add teams support to database.
Run this once to update the schema.
"""
import psycopg2
import os
from utils.logging_errors import write_log

def migrate_to_teams():
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        # Create teams table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS legal_saas.teams (
                id SERIAL PRIMARY KEY,
                clerk_org_id VARCHAR(100) NOT NULL,
                name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(clerk_org_id, name)
            );
        ''')
        
        # Create user_teams junction table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS legal_saas.user_teams (
                user_id INTEGER NOT NULL REFERENCES legal_saas.users(id) ON DELETE CASCADE,
                team_id INTEGER NOT NULL REFERENCES legal_saas.teams(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, team_id)
            );
        ''')
        
        # Drop teams column from users if it exists
        cur.execute('''
            ALTER TABLE legal_saas.users DROP COLUMN IF EXISTS teams;
        ''')
        
        conn.commit()
        cur.close()
        conn.close()
        
        write_log("Migration: Teams tables created successfully")
        print("Migration completed successfully")
        
    except Exception as e:
        write_log(f"Migration error: {e}")
        print(f"Migration failed: {e}")
        raise

if __name__ == '__main__':
    migrate_to_teams()
