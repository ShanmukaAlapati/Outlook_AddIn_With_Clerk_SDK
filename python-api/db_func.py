"""
Database functions for organization signup management.
All database operations are centralized here.
"""
import psycopg2
import os
import bcrypt
import uuid
from utils.logging_errors import write_log
from psycopg2.errorcodes import UNDEFINED_TABLE


def get_db_connection():
    """
    Establish database connection using DATABASE_URL from environment.
    
    Returns:
        psycopg2.connection: Database connection object
    
    Raises:
        Exception: If connection fails
    """
    try:
        return psycopg2.connect(os.getenv('DATABASE_URL'))
    except Exception as e:
        write_log(f"get_db_connection: Failed to connect - {e}")
        raise


def db_is_healthy() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        write_log("db_is_healthy: Database connection successful")
        return True
    except Exception as e:
        write_log(f"db_is_healthy: Failed - {e}")
        return False


def ensure_schema():
    """
    Create database schema and tables if they don't exist.
    Includes indexes for performance optimization.
    
    Tables created:
    - legal_saas.org_signups: Organization signup requests
    
    Raises:
        Exception: If schema creation fails
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('''
            CREATE SCHEMA IF NOT EXISTS legal_saas;

            CREATE TABLE IF NOT EXISTS legal_saas.org_signups (
                id BIGINT PRIMARY KEY,
                admin_name VARCHAR(255) NOT NULL,
                organization_name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                number_of_seats INTEGER DEFAULT 1,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                approved_by VARCHAR(100),
                rejected_at TIMESTAMP,
                rejected_by VARCHAR(100),
                rejection_reason TEXT,
                clerk_user_id VARCHAR(100),
                clerk_org_id VARCHAR(100),
                clerk_org_slug VARCHAR(200)
            );

            -- Ensure columns exist (migration for existing tables)
            ALTER TABLE legal_saas.org_signups ADD COLUMN IF NOT EXISTS clerk_user_id VARCHAR(100);
            ALTER TABLE legal_saas.org_signups ADD COLUMN IF NOT EXISTS clerk_org_id VARCHAR(100);
            ALTER TABLE legal_saas.org_signups ADD COLUMN IF NOT EXISTS clerk_org_slug VARCHAR(200);
            
            CREATE TABLE IF NOT EXISTS legal_saas.users (
                id SERIAL PRIMARY KEY,
                clerk_user_id VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) NOT NULL,
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                role VARCHAR(50),
                level INTEGER,
                clerk_org_id VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS legal_saas.teams (
                id SERIAL PRIMARY KEY,
                clerk_org_id VARCHAR(100) NOT NULL,
                name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(clerk_org_id, name)
            );

            CREATE TABLE IF NOT EXISTS legal_saas.user_teams (
                user_id INTEGER NOT NULL REFERENCES legal_saas.users(id) ON DELETE CASCADE,
                team_id INTEGER NOT NULL REFERENCES legal_saas.teams(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, team_id)
            );

            CREATE INDEX IF NOT EXISTS idx_users_email 
            ON legal_saas.users(email);
            
            CREATE INDEX IF NOT EXISTS idx_users_clerk_id 
            ON legal_saas.users(clerk_user_id);
            
            CREATE INDEX IF NOT EXISTS idx_org_signups_status 
            ON legal_saas.org_signups(status);
            
            CREATE INDEX IF NOT EXISTS idx_org_signups_email 
            ON legal_saas.org_signups(email);
            
            CREATE INDEX IF NOT EXISTS idx_org_signups_created 
            ON legal_saas.org_signups(created_at DESC);

            CREATE TABLE IF NOT EXISTS legal_saas.conversations (
                id SERIAL PRIMARY KEY,
                user1_id VARCHAR(100) NOT NULL,
                user2_id VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user1_id, user2_id)
            );

            CREATE TABLE IF NOT EXISTS legal_saas.messages (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER NOT NULL REFERENCES legal_saas.conversations(id),
                sender_id VARCHAR(100) NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
            ON legal_saas.messages(conversation_id);

            -- Matter Group Chats: multiple named chats per matter
            CREATE TABLE IF NOT EXISTS legal_saas.matter_group_chats (
                id SERIAL PRIMARY KEY,
                matter_id INTEGER NOT NULL,
                org_id VARCHAR(100) NOT NULL,
                created_by VARCHAR(100) NOT NULL,
                title VARCHAR(255) NOT NULL DEFAULT 'General',
                participants TEXT[] NOT NULL DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Migration: add title column if missing, drop unique constraint if exists
            ALTER TABLE legal_saas.matter_group_chats ADD COLUMN IF NOT EXISTS title VARCHAR(255) NOT NULL DEFAULT 'General';

            -- Drop the old UNIQUE(matter_id) constraint so multiple chats per matter are allowed
            DO $$
            DECLARE
                cname TEXT;
            BEGIN
                SELECT conname INTO cname
                FROM pg_constraint
                WHERE conrelid = 'legal_saas.matter_group_chats'::regclass
                  AND contype = 'u'
                  AND conname LIKE '%matter_id%'
                LIMIT 1;
                IF cname IS NOT NULL THEN
                    EXECUTE 'ALTER TABLE legal_saas.matter_group_chats DROP CONSTRAINT ' || quote_ident(cname);
                END IF;
            END$$;

            CREATE TABLE IF NOT EXISTS legal_saas.matter_chat_messages (
                id SERIAL PRIMARY KEY,
                chat_id INTEGER NOT NULL REFERENCES legal_saas.matter_group_chats(id) ON DELETE CASCADE,
                sender_id VARCHAR(100) NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_matter_chat_messages_chat_id
            ON legal_saas.matter_chat_messages(chat_id);

            CREATE TABLE IF NOT EXISTS legal_saas.notifications (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                type VARCHAR(50) NOT NULL,
                link VARCHAR(255),
                read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_notifications_user_id
            ON legal_saas.notifications(user_id);

            -- Core Fields
            CREATE TABLE IF NOT EXISTS legal_saas.core_fields (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                field_name VARCHAR(255) NOT NULL,
                field_type VARCHAR(100) NOT NULL,
                is_core BOOLEAN DEFAULT TRUE,
                comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Organization Customized Fields (Adoption of Core Fields)
            CREATE TABLE IF NOT EXISTS legal_saas.org_custom_fields (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id VARCHAR(100) NOT NULL,
                core_field_id UUID NOT NULL REFERENCES legal_saas.core_fields(id) ON DELETE CASCADE,
                is_active BOOLEAN DEFAULT TRUE,
                is_required BOOLEAN DEFAULT FALSE,
                display_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (org_id, core_field_id)
            );

            -- Migration: add display_name if it doesn't exist yet
            ALTER TABLE legal_saas.org_custom_fields ADD COLUMN IF NOT EXISTS display_name VARCHAR(255);

            CREATE INDEX IF NOT EXISTS idx_org_custom_fields_org_id
            ON legal_saas.org_custom_fields(org_id);
        ''')
        
        conn.commit()
        cur.close()
        conn.close()
        write_log("ensure_schema: Schema and tables created successfully")
        
        # Initialize additional schemas
        ensure_matter_settings_schema()
        
    except Exception as e:
        write_log(f"ensure_schema: Error - {e}")
        raise


def check_email_exists(email: str) -> dict:
    """
    Check if an email already exists in signups.
    
    Args:
        email (str): Email address to check
    
    Returns:
        dict: {"exists": bool, "status": str or None, "id": int or None}
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "SELECT id, status FROM legal_saas.org_signups WHERE email = %s",
            (email.lower().strip(),)
        )
        row = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if row:
            write_log(f"check_email_exists: Email {email} exists - id={row[0]}, status={row[1]}")
            return {
                "exists": True,
                "id": row[0],
                "status": row[1]
            }
        else:
            write_log(f"check_email_exists: Email {email} not found")
            return {
                "exists": False,
                "id": None,
                "status": None
            }
    
    except Exception as e:
        write_log(f"check_email_exists: Error - {e}")
        raise


def create_signup(signup_data: dict) -> dict:
    """
    Create a new organization signup request.
    
    Args:
        signup_data (dict): {
            "id": int,
            "adminName": str,
            "organizationName": str,
            "email": str,
            "password": str,
            "numberOfSeats": int
        }
    
    Returns:
        dict: {"success": bool, "signup_id": int, "message": str}
    
    Raises:
        Exception: If insertion fails
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Hash password
        password_hash = bcrypt.hashpw(
            signup_data['password'].encode(), 
            bcrypt.gensalt()
        ).decode()
        
        write_log(f"create_signup: Creating signup for email={signup_data['email']}")
        
        # Insert into database
        cur.execute(
            """
            INSERT INTO legal_saas.org_signups (
                id,
                admin_name,
                organization_name,
                email,
                password_hash,
                number_of_seats,
                status,
                clerk_user_id,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (
                signup_data['id'],
                signup_data['adminName'].strip(),
                signup_data['organizationName'].strip(),
                signup_data['email'].lower().strip(),
                password_hash,
                signup_data['numberOfSeats'],
                'pending',
                signup_data.get('clerk_user_id')
            )
        )
        
        inserted_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        write_log(f"create_signup: Signup created successfully - id={inserted_id}")
        
        return {
            "success": True,
            "signup_id": inserted_id,
            "message": "Signup created successfully"
        }
    
    except Exception as e:
        write_log(f"create_signup: Error - {e}")
        raise


def list_org_signups():
    """
    Fetch all organization signups.
    
    Returns:
        list: List of signup dictionaries with all details
    
    Raises:
        RuntimeError: If table doesn't exist
        Exception: For other database errors
    """
    try:
        write_log("list_org_signups: Fetching all signups")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT id, admin_name, organization_name, email,
                   number_of_seats, status, created_at, approved_at,
                   rejected_at, rejection_reason, clerk_org_id
            FROM legal_saas.org_signups
            ORDER BY created_at DESC;
            """
        )
        
        rows = cur.fetchall()
        cur.close()
        conn.close()

        data = []
        for r in rows:
            data.append({
                "id": r[0],
                "admin_name": r[1],
                "organization_name": r[2],
                "email": r[3],
                "number_of_seats": r[4],
                "status": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
                "approved_at": r[7].isoformat() if r[7] else None,
                "rejected_at": r[8].isoformat() if r[8] else None,
                "rejection_reason": r[9],
                "clerk_org_id": r[10],
            })
        
        write_log(f"list_org_signups: Found {len(data)} signups")
        return data

    except Exception as e:
        if getattr(e, "pgcode", None) == UNDEFINED_TABLE:
            msg = "Table legal_saas.org_signups does not exist"
            write_log(msg)
            raise RuntimeError(msg)
        write_log(f"list_org_signups: Error - {e}")
        raise


def list_pending_signups():
    """
    Fetch only pending signups (awaiting approval).
    
    Returns:
        list: List of pending signup dictionaries
    
    Raises:
        Exception: If query fails
    """
    try:
        write_log("list_pending_signups: Fetching pending signups")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT id, admin_name, organization_name, email,
                   number_of_seats, status, created_at
            FROM legal_saas.org_signups
            WHERE status = 'pending'
            ORDER BY created_at ASC;
            """
        )
        
        rows = cur.fetchall()
        cur.close()
        conn.close()

        data = []
        for r in rows:
            data.append({
                "id": r[0],
                "admin_name": r[1],
                "organization_name": r[2],
                "email": r[3],
                "number_of_seats": r[4],
                "status": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
            })
        
        write_log(f"list_pending_signups: Found {len(data)} pending signups")
        return data
    
    except Exception as e:
        write_log(f"list_pending_signups: Error - {e}")
        raise


def get_signup_by_id(signup_id: int):
    """
    Fetch a single signup by ID.
    
    Args:
        signup_id (int): ID of the signup to fetch
    
    Returns:
        dict: Signup details or None if not found
    
    Raises:
        Exception: If query fails
    """
    try:
        write_log(f"get_signup_by_id: Fetching signup {signup_id}")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT id, admin_name, organization_name, email,
                   number_of_seats, status, created_at, approved_at,
                   rejected_at, rejection_reason, clerk_user_id,
                   clerk_org_id, clerk_org_slug, password_hash
            FROM legal_saas.org_signups
            WHERE id = %s;
            """,
            (signup_id,)
        )
        
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            write_log(f"get_signup_by_id: Signup {signup_id} not found")
            return None
        
        data = {
            "id": row[0],
            "admin_name": row[1],
            "organization_name": row[2],
            "email": row[3],
            "number_of_seats": row[4],
            "status": row[5],
            "created_at": row[6].isoformat() if row[6] else None,
            "approved_at": row[7].isoformat() if row[7] else None,
            "rejected_at": row[8].isoformat() if row[8] else None,
            "rejection_reason": row[9],
            "clerk_user_id": row[10],
            "clerk_org_id": row[11],
            "clerk_org_slug": row[12],
            "password_hash": row[13]
        }
        
        write_log(f"get_signup_by_id: Found signup {signup_id}")
        return data
    
    except Exception as e:
        write_log(f"get_signup_by_id: Error - {e}")
        raise


def get_db_stats():
    """
    Get database statistics (count by status).
    
    Returns:
        dict: {
            "total": int,
            "pending": int,
            "approved": int,
            "rejected": int
        }
    
    Raises:
        Exception: If query fails
    """
    try:
        write_log("get_db_stats: Fetching database statistics")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'approved') as approved,
                COUNT(*) FILTER (WHERE status = 'rejected') as rejected
            FROM legal_saas.org_signups;
            """
        )
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        stats = {
            "total": row[0] or 0,
            "pending": row[1] or 0,
            "approved": row[2] or 0,
            "rejected": row[3] or 0
        }
        
        write_log(f"get_db_stats: {stats}")
        return stats
    
    except Exception as e:
        write_log(f"get_db_stats: Error - {e}")
        raise


def approve_signup(signup_id: int, approved_by: str, clerk_data: dict):
    """
    Approve a pending signup and update with Clerk info.
    
    Args:
        signup_id (int): ID of signup to approve
        approved_by (str): User ID of super admin approving
        clerk_data (dict): {
            "clerk_user_id": str,
            "clerk_org_id": str,
            "clerk_org_slug": str
        }
    
    Returns:
        dict: {"success": bool, "message": str}
    
    Raises:
        Exception: If update fails
    """
    try:
        write_log(f"approve_signup: Approving signup {signup_id}")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            UPDATE legal_saas.org_signups
            SET status = 'approved',
                approved_at = NOW(),
                approved_by = %s,
                clerk_user_id = %s,
                clerk_org_id = %s,
                clerk_org_slug = %s
            WHERE id = %s AND status = 'pending'
            RETURNING id
            """,
            (
                approved_by,
                clerk_data.get('clerk_user_id'),
                clerk_data.get('clerk_org_id'),
                clerk_data.get('clerk_org_slug'),
                signup_id
            )
        )
        
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if result:
            write_log(f"approve_signup: Signup {signup_id} approved successfully")
            return {
                "success": True,
                "message": "Signup approved successfully"
            }
        else:
            write_log(f"approve_signup: Signup {signup_id} not found or not pending")
            return {
                "success": False,
                "message": "Signup not found or already processed"
            }
    
    except Exception as e:
        write_log(f"approve_signup: Error - {e}")
        raise


def reject_signup(signup_id: int, rejected_by: str, reason: str):
    """
    Reject a pending signup.
    
    Args:
        signup_id (int): ID of signup to reject
        rejected_by (str): User ID of super admin rejecting
        reason (str): Reason for rejection
    
    Returns:
        dict: {"success": bool, "message": str}
    
    Raises:
        Exception: If update fails
    """
    try:
        write_log(f"reject_signup: Rejecting signup {signup_id}")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            UPDATE legal_saas.org_signups
            SET status = 'rejected',
                rejected_at = NOW(),
                rejected_by = %s,
                rejection_reason = %s
            WHERE id = %s AND status = 'pending'
            RETURNING id
            """,
            (rejected_by, reason, signup_id)
        )
        
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if result:
            write_log(f"reject_signup: Signup {signup_id} rejected successfully")
            return {
                "success": True,
                "message": "Signup rejected successfully"
            }
        else:
            write_log(f"reject_signup: Signup {signup_id} not found or not pending")
            return {
                "success": False,
                "message": "Signup not found or already processed"
            }
    
    except Exception as e:
        write_log(f"reject_signup: Error - {e}")
        raise



def create_local_user(user_data: dict) -> dict:
    """
    Create or update a user in the local database.
    
    Args:
        user_data (dict): {
            "clerk_user_id": str,
            "email": str,
            "first_name": str,
            "last_name": str,
            "role": str,
            "level": int,
            "clerk_org_id": str,
            "teams": list
        }
    
    Returns:
        dict: {"success": bool, "id": int, "message": str}
    """
    try:
        teams = user_data.get('teams', [])
        write_log(f"create_local_user: Saving user {user_data.get('email')} with teams={teams}")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute(
            "SELECT id FROM legal_saas.users WHERE clerk_user_id = %s",
            (user_data['clerk_user_id'],)
        )
        exists = cur.fetchone()
        
        if exists:
            user_id = exists[0]
            # Update existing user
            cur.execute(
                """
                UPDATE legal_saas.users
                SET email = %s,
                    first_name = %s,
                    last_name = %s,
                    role = %s,
                    level = %s,
                    clerk_org_id = %s
                WHERE id = %s
                """,
                (
                    user_data['email'],
                    user_data.get('first_name'),
                    user_data.get('last_name'),
                    user_data.get('role'),
                    user_data.get('level'),
                    user_data.get('clerk_org_id'),
                    user_id
                )
            )
            action = "updated"
            cur.execute("DELETE FROM legal_saas.user_teams WHERE user_id = %s", (user_id,))
        else:
            # Insert new user
            cur.execute(
                """
                INSERT INTO legal_saas.users (
                    clerk_user_id,
                    email,
                    first_name,
                    last_name,
                    role,
                    level,
                    clerk_org_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user_data['clerk_user_id'],
                    user_data['email'],
                    user_data.get('first_name'),
                    user_data.get('last_name'),
                    user_data.get('role'),
                    user_data.get('level'),
                    user_data.get('clerk_org_id')
                )
            )
            user_id = cur.fetchone()[0]
            action = "created"
        
        # Save teams to junction table
        if teams and user_data.get('clerk_org_id'):
            for team_name in teams:
                cur.execute(
                    """
                    INSERT INTO legal_saas.teams (clerk_org_id, name)
                    VALUES (%s, %s)
                    ON CONFLICT (clerk_org_id, name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                    (user_data.get('clerk_org_id'), team_name)
                )
                team_id = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO legal_saas.user_teams (user_id, team_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (user_id, team_id)
                )
            
        conn.commit()
        cur.close()
        conn.close()
        
        write_log(f"create_local_user: User {action} successfully - id={user_id}, teams={teams}")
        
        return {
            "success": True,
            "id": user_id,
            "message": f"User {action} successfully"
        }
        
    except Exception as e:
        write_log(f"create_local_user: Error - {e}")
        return {"success": False, "message": str(e)}


def get_users_by_org(clerk_org_id: str) -> list:
    """
    Fetch all users belonging to a specific organization with team names.
    
    Args:
        clerk_org_id (str): The Clerk organization ID.
        
    Returns:
        list: List of user dictionaries with team names.
    """
    try:
        write_log(f"get_users_by_org: Fetching users for org {clerk_org_id}")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT u.id, u.clerk_user_id, u.email, u.first_name, u.last_name, u.role, u.level, u.created_at,
                   COALESCE(array_agg(t.name) FILTER (WHERE t.name IS NOT NULL), ARRAY[]::text[]) as team_names
            FROM legal_saas.users u
            LEFT JOIN legal_saas.user_teams ut ON u.id = ut.user_id
            LEFT JOIN legal_saas.teams t ON ut.team_id = t.id
            WHERE u.clerk_org_id = %s
            GROUP BY u.id, u.clerk_user_id, u.email, u.first_name, u.last_name, u.role, u.level, u.created_at
            ORDER BY u.created_at DESC
            """,
            (clerk_org_id,)
        )
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        users = []
        for r in rows:
            users.append({
                "id": r[0],
                "clerk_user_id": r[1],
                "email": r[2],
                "first_name": r[3],
                "last_name": r[4],
                "role": r[5],
                "level": r[6],
                "created_at": r[7].isoformat() if r[7] else None,
                "teams": list(r[8]) if r[8] else []
            })
            
        write_log(f"get_users_by_org: Found {len(users)} users with teams")
        return users
        
    except Exception as e:
        write_log(f"get_users_by_org: Error - {e}")
        raise



def check_user_exists_in_org(email: str, clerk_org_id: str) -> bool:
    """
    Check if a user with the given email already exists in a specific organization.
    
    Args:
        email (str): The email to check.
        clerk_org_id (str): The Clerk organization ID.
        
    Returns:
        bool: True if user exists, False otherwise.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "SELECT id FROM legal_saas.users WHERE LOWER(email) = LOWER(%s) AND clerk_org_id = %s",
            (email.strip(), clerk_org_id)
        )
        exists = cur.fetchone() is not None
        
        cur.close()
        conn.close()
        
        return exists
        
    except Exception as e:
        write_log(f"check_user_exists_in_org: Error - {e}")
        return False



def update_local_user_fields(clerk_user_id: str, **kwargs) -> dict:
    """
    Update specific fields for a local user.
    
    Args:
        clerk_user_id (str): The Clerk user ID.
        **kwargs: Key-value pairs of fields to update (e.g., level=2, role='org:admin', teams=['marketing']).
        
    Returns:
        dict: {"success": bool, "message": str}
    """
    try:
        allowed_fields = {'email', 'first_name', 'last_name', 'role', 'level', 'clerk_org_id'}
        teams = kwargs.pop('teams', None)
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates and teams is None:
            return {"success": False, "message": "No valid fields to update"}
            
        write_log(f"update_local_user_fields: Updating user {clerk_user_id} with {updates}, teams={teams}")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get user ID and org ID
        cur.execute(
            "SELECT id, clerk_org_id FROM legal_saas.users WHERE clerk_user_id = %s",
            (clerk_user_id,)
        )
        result = cur.fetchone()
        
        if not result:
            cur.close()
            conn.close()
            return {"success": False, "message": "User not found"}
            
        user_id, org_id = result
        
        # Update basic fields
        if updates:
            set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
            values = list(updates.values())
            values.append(clerk_user_id)
            
            cur.execute(
                f"""
                UPDATE legal_saas.users
                SET {set_clause}
                WHERE clerk_user_id = %s
                """,
                tuple(values)
            )
        
        # Update teams
        if teams is not None and org_id:
            # Clear existing teams
            cur.execute("DELETE FROM legal_saas.user_teams WHERE user_id = %s", (user_id,))
            
            # Add new teams
            for team_name in teams:
                cur.execute(
                    """
                    INSERT INTO legal_saas.teams (clerk_org_id, name)
                    VALUES (%s, %s)
                    ON CONFLICT (clerk_org_id, name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                    (org_id, team_name)
                )
                team_id = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO legal_saas.user_teams (user_id, team_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (user_id, team_id)
                )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"success": True, "message": "User updated successfully"}
            
    except Exception as e:
        write_log(f"update_local_user_fields: Error - {e}")
        return {"success": False, "message": str(e)}


def delete_org_from_db(clerk_org_id: str) -> dict:
    """
    Delete an organization and all its members from the local database.

    Args:
        clerk_org_id (str): The Clerk organization ID to delete.

    Returns:
        dict: {"success": bool, "message": str, "users_deleted": int, "signup_deleted": bool}

    Raises:
        Exception: If deletion fails
    """
    try:
        write_log(f"delete_org_from_db: Deleting org {clerk_org_id} from local DB")

        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Fetch user IDs (local and Clerk) BEFORE deleting them
        cur.execute(
            "SELECT id, clerk_user_id FROM legal_saas.users WHERE clerk_org_id = %s",
            (clerk_org_id,)
        )
        user_rows = cur.fetchall()
        user_ids = [r[0] for r in user_rows]
        clerk_user_ids = [r[1] for r in user_rows if r[1]]

        # 2. Delete Matters associated with this org
        cur.execute(
            "DELETE FROM legal_saas.matters WHERE org_id = %s",
            (clerk_org_id,)
        )
        matters_deleted = cur.rowcount
        write_log(f"delete_org_from_db: Deleted {matters_deleted} matters")

        # 3. Delete Messages and Conversations for these users
        if clerk_user_ids:
            # Delete messages sent by these users
            cur.execute(
                "DELETE FROM legal_saas.messages WHERE sender_id = ANY(%s)",
                (clerk_user_ids,)
            )
            messages_deleted = cur.rowcount
            
            # Delete conversations involving these users
            cur.execute(
                "DELETE FROM legal_saas.conversations WHERE user1_id = ANY(%s) OR user2_id = ANY(%s)",
                (clerk_user_ids, clerk_user_ids)
            )
            conversations_deleted = cur.rowcount
            write_log(f"delete_org_from_db: Deleted {messages_deleted} messages and {conversations_deleted} conversations")

        # 4. Delete user_teams entries for these users
        if user_ids:
            cur.execute(
                "DELETE FROM legal_saas.user_teams WHERE user_id = ANY(%s)",
                (user_ids,)
            )

        # 5. Delete users belonging to this org
        cur.execute(
            "DELETE FROM legal_saas.users WHERE clerk_org_id = %s",
            (clerk_org_id,)
        )
        users_deleted = cur.rowcount

        # 6. Delete teams belonging to this org
        cur.execute(
            "DELETE FROM legal_saas.teams WHERE clerk_org_id = %s",
            (clerk_org_id,)
        )

        # 7. Delete the org signup row
        cur.execute(
            "DELETE FROM legal_saas.org_signups WHERE clerk_org_id = %s",
            (clerk_org_id,)
        )
        signup_deleted = cur.rowcount > 0

        conn.commit()
        cur.close()
        conn.close()

        write_log(
            f"delete_org_from_db: Finished cleanup for org {clerk_org_id} - "
            f"users={users_deleted}, matters={matters_deleted}, signup={signup_deleted}"
        )

        return {
            "success": True,
            "message": "Organization data deleted from local DB",
            "users_deleted": users_deleted,
            "matters_deleted": matters_deleted,
            "signup_deleted": signup_deleted
        }

    except Exception as e:
        write_log(f"delete_org_from_db: Error deleting org {clerk_org_id} - {e}")
        raise


def delete_local_user(clerk_user_id: str, clerk_org_id: str) -> dict:
    """
    Remove a single user from the local database for a specific organization.

    Args:
        clerk_user_id (str): The Clerk user ID.
        clerk_org_id (str): The Clerk organization ID.

    Returns:
        dict: {"success": bool, "message": str}
    """
    try:
        write_log(f"delete_local_user: Removing user {clerk_user_id} from org {clerk_org_id}")

        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Get the local user ID
        cur.execute(
            "SELECT id FROM legal_saas.users WHERE clerk_user_id = %s AND clerk_org_id = %s",
            (clerk_user_id, clerk_org_id)
        )
        result = cur.fetchone()

        if not result:
            cur.close()
            conn.close()
            write_log(f"delete_local_user: User {clerk_user_id} not found in org {clerk_org_id}")
            return {"success": False, "message": "User not found in local DB"}

        local_user_id = result[0]

        # 2. Remove user_teams entries
        cur.execute(
            "DELETE FROM legal_saas.user_teams WHERE user_id = %s",
            (local_user_id,)
        )
        write_log(f"delete_local_user: Removed user_teams for user {clerk_user_id}")

        # 3. Remove the user row
        cur.execute(
            "DELETE FROM legal_saas.users WHERE id = %s",
            (local_user_id,)
        )

        conn.commit()
        cur.close()
        conn.close()

        write_log(f"delete_local_user: Successfully removed user {clerk_user_id} from local DB")
        return {"success": True, "message": "User removed from local DB"}

    except Exception as e:
        write_log(f"delete_local_user: Error - {e}")
        return {"success": False, "message": str(e)}


# ============================================================================
# MATTER FUNCTIONS
# ============================================================================

def create_matters_table():
    """
    Idempotent migration: ensures legal_saas.matters table matches schema.
    Adds missing columns like 'heading', 'assigned_to', and 'related_to'.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Ensure table exists with core columns
        cur.execute("""
            CREATE TABLE IF NOT EXISTS legal_saas.matters (
                id           SERIAL PRIMARY KEY,
                uuid         VARCHAR(100) UNIQUE,
                org_id       VARCHAR(100) NOT NULL,
                heading      VARCHAR(255) NOT NULL,
                name         VARCHAR(255) NOT NULL,
                created_by   VARCHAR(100) NOT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_to  TEXT[],
                status       VARCHAR(50) DEFAULT 'open',
                related_to   TEXT
            );
        """)

        # 2. Migration for existing tables
        migrations = [
            "ALTER TABLE legal_saas.matters ADD COLUMN IF NOT EXISTS heading VARCHAR(255) DEFAULT ''",
            "ALTER TABLE legal_saas.matters ADD COLUMN IF NOT EXISTS assigned_to TEXT[]",
            "ALTER TABLE legal_saas.matters ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'pending'",
            "ALTER TABLE legal_saas.matters ADD COLUMN IF NOT EXISTS priority VARCHAR(50) DEFAULT 'medium'",
            "ALTER TABLE legal_saas.matters ADD COLUMN IF NOT EXISTS related_to TEXT",
            "ALTER TABLE legal_saas.matters ADD COLUMN IF NOT EXISTS content TEXT",
            "ALTER TABLE legal_saas.matters ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb",
            "ALTER TABLE legal_saas.matters ADD COLUMN IF NOT EXISTS uuid VARCHAR(100) UNIQUE"
        ]
        
        for sql in migrations:
            try:
                cur.execute(sql)
            except Exception as e:
                write_log(f"create_matters_table: Migration skip - {sql} - {e}")
                conn.rollback()

        # 3. Indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_matters_org_id ON legal_saas.matters(org_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_matters_created_by ON legal_saas.matters(created_by)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_matters_assigned_to ON legal_saas.matters USING GIN(assigned_to)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_matters_status ON legal_saas.matters(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_matters_priority ON legal_saas.matters(priority)")

        # Update table for matter_type and matter_subtype
        cur.execute("ALTER TABLE legal_saas.matters ADD COLUMN IF NOT EXISTS matter_type_id INTEGER")
        cur.execute("ALTER TABLE legal_saas.matters ADD COLUMN IF NOT EXISTS matter_subtype_id INTEGER")
        
        conn.commit()
        cur.close()
        conn.close()
        write_log("create_matters_table: matters table schema ensured")

    except Exception as e:
        write_log(f"create_matters_table: Error - {e}")
        raise




def ensure_matter_settings_schema():
    """
    Create tables for matter types, sub-types, and field associations.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Matter Types Table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS legal_saas.matter_types (
                id SERIAL PRIMARY KEY,
                org_id VARCHAR(100) NOT NULL,
                name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(org_id, name)
            );
        ''')
        
        # 2. Matter Sub-types Table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS legal_saas.matter_subtypes (
                id SERIAL PRIMARY KEY,
                matter_type_id INTEGER NOT NULL REFERENCES legal_saas.matter_types(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(matter_type_id, name)
            );
        ''')
        
        # 3. Matter Sub-type Fields Association Table (Mapping) - uses core_fields (UUID)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS legal_saas.matter_subtype_fields (
                id SERIAL PRIMARY KEY,
                matter_subtype_id INTEGER NOT NULL REFERENCES legal_saas.matter_subtypes(id) ON DELETE CASCADE,
                core_field_id VARCHAR(100) NOT NULL,
                display_name  VARCHAR(255),
                display_order INTEGER DEFAULT 0,
                is_required BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(matter_subtype_id, core_field_id)
            );
        ''')
        
        # Migration: handle old table that had field_definition_id NOT NULL
        migrations = [
            # Add new columns if missing
            "ALTER TABLE legal_saas.matter_subtype_fields ADD COLUMN IF NOT EXISTS core_field_id VARCHAR(100)",
            "ALTER TABLE legal_saas.matter_subtype_fields ADD COLUMN IF NOT EXISTS display_name VARCHAR(255)",
            "ALTER TABLE legal_saas.matter_subtype_fields ADD COLUMN IF NOT EXISTS options JSONB DEFAULT '[]'::jsonb",
            # Make old field_definition_id nullable so new inserts (using core_field_id only) work
            "ALTER TABLE legal_saas.matter_subtype_fields ALTER COLUMN field_definition_id DROP NOT NULL",
        ]
        for sql in migrations:
            try:
                cur.execute(sql)
                conn.commit()
            except Exception as me:
                write_log(f"ensure_matter_settings_schema: migration skip ({me})")
                conn.rollback()

        # Add UNIQUE constraint on (matter_subtype_id, core_field_id) if it doesn't exist yet
        try:
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'matter_subtype_fields_matter_subtype_id_core_field_id_key'
                    ) THEN
                        ALTER TABLE legal_saas.matter_subtype_fields
                            ADD CONSTRAINT matter_subtype_fields_matter_subtype_id_core_field_id_key
                            UNIQUE (matter_subtype_id, core_field_id);
                    END IF;
                END $$;
            """)
            conn.commit()
        except Exception as ce:
            write_log(f"ensure_matter_settings_schema: unique constraint skip ({ce})")
            conn.rollback()

        
        conn.commit()
        cur.close()
        conn.close()
        write_log("ensure_matter_settings_schema: Tables created successfully")
    except Exception as e:
        write_log(f"ensure_matter_settings_schema: Error - {e}")

def get_matter_types(org_id: str) -> list:
    """Fetch all matter types for an organization."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, org_id, name, created_at FROM legal_saas.matter_types WHERE org_id = %s ORDER BY name ASC",
            (org_id,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"id": r[0], "org_id": r[1], "name": r[2], "created_at": r[3].isoformat() if r[3] else None} for r in rows]
    except Exception as e:
        write_log(f"get_matter_types: Error - {e}")
        return []

def create_matter_type(org_id: str, name: str) -> dict:
    """Create a new matter type."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO legal_saas.matter_types (org_id, name) VALUES (%s, %s) RETURNING id, org_id, name, created_at",
            (org_id, name)
        )
        r = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return {"id": r[0], "org_id": r[1], "name": r[2], "created_at": r[3].isoformat() if r[3] else None}
    except Exception as e:
        write_log(f"create_matter_type: Error - {e}")
        return None

def get_matter_subtypes(matter_type_id: int) -> list:
    """Fetch all sub-types for a specific matter type."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, matter_type_id, name, created_at FROM legal_saas.matter_subtypes WHERE matter_type_id = %s ORDER BY name ASC",
            (matter_type_id,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"id": r[0], "matter_type_id": r[1], "name": r[2], "created_at": r[3].isoformat() if r[3] else None} for r in rows]
    except Exception as e:
        write_log(f"get_matter_subtypes: Error - {e}")
        return []

def create_matter_subtype(matter_type_id: int, name: str) -> dict:
    """Create a new matter sub-type."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO legal_saas.matter_subtypes (matter_type_id, name) VALUES (%s, %s) RETURNING id, matter_type_id, name, created_at",
            (matter_type_id, name)
        )
        r = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return {"id": r[0], "matter_type_id": r[1], "name": r[2], "created_at": r[3].isoformat() if r[3] else None}
    except Exception as e:
        write_log(f"create_matter_subtype: Error - {e}")
        return None

def get_matter_subtype_fields(matter_subtype_id: int) -> list:
    """Fetch associated core fields for a matter sub-type."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT cf.id, cf.field_name, cf.field_type,
                   COALESCE(msf.display_name, cf.field_name) AS resolved_display_name,
                   msf.display_order, msf.is_required,
                   COALESCE(msf.options, '[]'::jsonb) AS options
            FROM legal_saas.core_fields cf
            JOIN legal_saas.matter_subtype_fields msf ON cf.id::text = msf.core_field_id
            WHERE msf.matter_subtype_id = %s
            ORDER BY msf.display_order ASC
            """,
            (matter_subtype_id,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "id": str(r[0]),
                "field_name": r[1],
                "field_type": r[2],
                "display_name": r[3],
                "display_order": r[4],
                "is_required": r[5],
                "options": r[6] if r[6] else []
            } for r in rows
        ]
    except Exception as e:
        write_log(f"get_matter_subtype_fields: Error - {e}")
        return []

def update_matter_subtype_fields(matter_subtype_id: int, field_data: list) -> bool:
    """
    Sync associated core fields for a matter sub-type.
    field_data: list of dicts [{
        "field_id": str (UUID),
        "display_order": int,
        "is_required": bool,
        "display_name": str|None,
        "options": list|None  # For dropdown/checkbox/radio fields
    }]
    """
    import json
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Remove existing associations
        cur.execute("DELETE FROM legal_saas.matter_subtype_fields WHERE matter_subtype_id = %s", (matter_subtype_id,))
        
        # 2. Insert new associations
        for item in field_data:
            options = item.get('options') or []
            cur.execute(
                """
                INSERT INTO legal_saas.matter_subtype_fields
                    (matter_subtype_id, core_field_id, display_name, display_order, is_required, options)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (matter_subtype_id, core_field_id) DO UPDATE
                    SET display_name = EXCLUDED.display_name,
                        display_order = EXCLUDED.display_order,
                        is_required = EXCLUDED.is_required,
                        options = EXCLUDED.options
                """,
                (
                    matter_subtype_id,
                    str(item['field_id']),
                    item.get('display_name') or None,
                    item.get('display_order', 0),
                    item.get('is_required', False),
                    json.dumps(options)
                )
            )
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        write_log(f"update_matter_subtype_fields: Error - {e}")
        return False


def create_field_definitions_table():
    """Idempotent migration for field definitions table."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS legal_saas.field_definitions (
                id           SERIAL PRIMARY KEY,
                org_id       VARCHAR(100) NOT NULL,
                name         VARCHAR(255) NOT NULL,
                type         VARCHAR(50) NOT NULL,
                config       JSONB DEFAULT '{}'::jsonb,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_field_definitions_org ON legal_saas.field_definitions(org_id)")
        conn.commit()
        cur.close()
        conn.close()
        write_log("create_field_definitions_table: field_definitions table ensured")
    except Exception as e:
        write_log(f"create_field_definitions_table: Error - {e}")

def get_field_definitions(org_id: str) -> list:
    """Fetch all field definitions for an org."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, org_id, name, type, config, created_at FROM legal_saas.field_definitions WHERE org_id = %s ORDER BY created_at ASC",
            (org_id,)
        )
        rows = cur.fetchall()
        defs = []
        for r in rows:
            defs.append({
                'id': r[0], 'org_id': r[1], 'name': r[2],
                'type': r[3], 'config': r[4], 'created_at': r[5].isoformat() if r[5] else None
            })
        cur.close()
        conn.close()
        return defs
    except Exception as e:
        write_log(f"get_field_definitions: Error - {e}")
        return []

def create_field_definition(org_id: str, name: str, ftype: str, config: dict = None) -> dict:
    """Create a new field definition."""
    import json
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO legal_saas.field_definitions (org_id, name, type, config)
            VALUES (%s, %s, %s, %s)
            RETURNING id, org_id, name, type, config, created_at
            """,
            (org_id, name, ftype, json.dumps(config or {}))
        )
        r = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return {
            'id': r[0], 'org_id': r[1], 'name': r[2],
            'type': r[3], 'config': r[4], 'created_at': r[5].isoformat() if r[5] else None
        }
    except Exception as e:
        write_log(f"create_field_definition: Error - {e}")
        return None
def delete_field_definition(id: int, org_id: str) -> bool:
    """Delete a field definition."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM legal_saas.field_definitions WHERE id = %s AND org_id = %s",
            (id, org_id)
        )
        conn.commit()
        count = cur.rowcount
        cur.close()
        conn.close()
        return count > 0
    except Exception as e:
        write_log(f"delete_field_definition: Error - {e}")
        return False

def update_field_definition(id: int, org_id: str, name: str, ftype: str, config: dict) -> dict:
    """Update an existing field definition."""
    import json
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE legal_saas.field_definitions
            SET name = %s, type = %s, config = %s
            WHERE id = %s AND org_id = %s
            RETURNING id, org_id, name, type, config, created_at
            """,
            (name, ftype, json.dumps(config or {}), id, org_id)
        )
        r = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if not r:
            return None
        return {
            'id': r[0], 'org_id': r[1], 'name': r[2],
            'type': r[3], 'config': r[4], 'created_at': r[5].isoformat() if r[5] else None
        }
    except Exception as e:
        write_log(f"update_field_definition: Error - {e}")
        return None

def create_matter(org_id: str, created_by: str, heading: str, name: str,
                  content: str, assigned_to: list, related_to: str = None, 
                  priority: str = 'medium', status: str = 'pending',
                  metadata: dict = None) -> dict:
    """
    Insert a new matter with the updated schema.

    Args:
        org_id       : Clerk org ID
        created_by   : clerk_user_id of creator
        heading      : short heading/title
        content      : detailed content/description
        assigned_to  : list of clerk_user_id strings
        related_to   : optional related_to field
        matter_type_id: Optional ID of the matter type
        matter_subtype_id: Optional ID of the matter subtype

    Returns:
        dict with full matter data
    """
    import json
    import uuid
    import psycopg2.extras
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        m_uuid = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO legal_saas.matters 
            (org_id, created_by, heading, name, content, assigned_to, related_to, priority, status, metadata, uuid, matter_type_id, matter_subtype_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, uuid, created_at
            """,
            (
                org_id, created_by, heading, heading, content, assigned_to, 
                related_to, priority, status, 
                psycopg2.extras.Json(metadata) if metadata else None,
                m_uuid, matter_type_id, matter_subtype_id
            )
        )
        
        res = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        write_log(f"create_matter: Created matter id={res[0]} uuid={res[1]} in org {org_id}")

        return {
            "id": res[0],
            "uuid": res[1],
            "created_at": res[2].isoformat() if res[2] else None,
            "name": heading, # Assuming 'name' is now derived from 'heading'
            "created_by": created_by,
            "assignees": assigned_to,
            "priority": priority,
            "status": status,
            "org_id": org_id,
            "metadata": metadata,
            "matter_type_id": matter_type_id,
            "matter_subtype_id": matter_subtype_id
        }
    except Exception as e:
        write_log(f"create_matter: Error - {e}")
        raise


def get_matters_for_user(clerk_user_id: str, org_id: str) -> dict:
    """
    Return all matters relevant to the user within their org using the new schema.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        def rows_to_dicts(rows):
            out = []
            for r in rows:
                out.append({
                    "id": r[0],
                    "org_id": r[1],
                    "created_by": r[2],
                    "heading": r[3],
                    "name": r[4],
                    "content": r[5],
                    "assignees": r[6] or [],
                    "related_to": r[7],
                    "created_at": r[8].isoformat() if r[8] else None,
                    "status": r[9],
                    "priority": r[10],
                    "metadata": r[11],
                    "uuid": r[12]
                })
            return out

        # 1. Matters created by this user
        cur.execute(
            """
            SELECT id, org_id, created_by, heading, name, content, assigned_to, related_to, created_at, status, priority, metadata, uuid
            FROM legal_saas.matters
            WHERE created_by = %s AND org_id = %s
            ORDER BY created_at DESC
            """,
            (clerk_user_id, org_id)
        )
        created_rows = cur.fetchall()

        # 2. Matters assigned to this user (but not created by them)
        cur.execute(
            """
            SELECT id, org_id, created_by, heading, name, content, assigned_to, related_to, created_at, status, priority, metadata, uuid
            FROM legal_saas.matters
            WHERE %s = ANY(assigned_to) AND org_id = %s AND created_by != %s
            ORDER BY created_at DESC
            """,
            (clerk_user_id, org_id, clerk_user_id)
        )
        assigned_rows = cur.fetchall()

        cur.close()
        conn.close()

        return {
            "created": rows_to_dicts(created_rows),
            "assigned": rows_to_dicts(assigned_rows),
        }

    except Exception as e:
        write_log(f"get_matters_for_user: Error - {e}")
        raise


def get_matter_by_id(matter_id: int, requesting_user_id: str) -> dict | None:
    """
    Fetch a single matter by ID using the new schema.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, org_id, created_by, heading, name, content, assigned_to, related_to, created_at, status, priority, metadata, uuid
            FROM legal_saas.matters
            WHERE id = %s
            """,
            (matter_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return None

        # Access control: creator or assignee only
        assigned_to = row[6] or []
        if requesting_user_id != row[2] and requesting_user_id not in assigned_to:
            write_log(f"get_matter_by_id: Access denied for user {requesting_user_id} on matter {matter_id}")
            return None

        return {
            "id": row[0],
            "org_id": row[1],
            "created_by": row[2],
            "heading": row[3],
            "name": row[4],
            "content": row[5],
            "assignees": assigned_to,
            "related_to": row[7],
            "created_at": row[8].isoformat() if row[8] else None,
            "status": row[9],
            "priority": row[10],
            "metadata": row[11],
            "uuid": row[12]
        }
    except Exception as e:
        write_log(f"get_matter_by_id: Error - {e}")
        raise


# ============================================================================
# CHAT FUNCTIONS
# ============================================================================

def normalize_pair(u1, u2):
    return (u1, u2) if u1 < u2 else (u2, u1)

def create_direct_conversation(user1_id: str, user2_id: str) -> int:
    """
    Get or create a 1-to-1 conversation between user1 and user2.
    """
    try:
        u1, u2 = normalize_pair(user1_id, user2_id)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if exists
        cur.execute(
            """
            SELECT id FROM legal_saas.conversations
            WHERE user1_id = %s AND user2_id = %s
            """,
            (u1, u2)
        )
        row = cur.fetchone()
        
        if row:
            conv_id = row[0]
            write_log(f"create_direct_conversation: Found existing conv {conv_id}")
        else:
            cur.execute(
                """
                INSERT INTO legal_saas.conversations (user1_id, user2_id)
                VALUES (%s, %s)
                RETURNING id
                """,
                (u1, u2)
            )
            conv_id = cur.fetchone()[0]
            conn.commit()
            write_log(f"create_direct_conversation: Created new conv {conv_id}")
            conn.commit()
            
        cur.close()
        conn.close()
        return conv_id
        
    except Exception as e:
        write_log(f"create_direct_conversation: Error - {e}")
        raise

def get_conversation_messages(conversation_id: int, limit: int = 50) -> list:
    """
    Fetch recent messages for a conversation.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT id, sender_id, text, created_at
            FROM legal_saas.messages
            WHERE conversation_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (conversation_id, limit)
        )
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        messages = []
        for r in rows:
            messages.append({
                "id": r[0],
                "sender_id": r[1],
                "text": r[2],
                "created_at": r[3].isoformat() if r[3] else None
            })
            
        # Return reversed (oldest first) for UI, or handle in UI
        # We'll return newest-first from DB, but usually UI wants oldest-first to append
        return messages
        
    except Exception as e:
        write_log(f"get_conversation_messages: Error - {e}")
        return []

def create_message(conversation_id: int, sender_id: str, text: str) -> dict:
    """
    Insert a new message.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            INSERT INTO legal_saas.messages (conversation_id, sender_id, text)
            VALUES (%s, %s, %s)
            RETURNING id, created_at
            """,
            (conversation_id, sender_id, text)
        )
        
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return {
            "id": row[0],
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "text": text,
            "created_at": row[1].isoformat() if row[1] else None
        }
        
    except Exception as e:
        write_log(f"create_message: Error - {e}")
        raise


# ===== MATTER GROUP CHAT FUNCTIONS =====

def create_matter_chat(matter_id: int, org_id: str, created_by: str, title: str, participants: list) -> dict:
    """
    Create a new named group chat for a matter.
    Multiple chats can exist per matter.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Ensure creator is always in participants
        if created_by not in participants:
            participants = [created_by] + participants
        cur.execute(
            """
            INSERT INTO legal_saas.matter_group_chats (matter_id, org_id, created_by, title, participants)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, matter_id, org_id, created_by, title, participants, created_at
            """,
            (matter_id, org_id, created_by, title.strip() or "General", participants)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        write_log(f"create_matter_chat: Created chat '{title}' (id={row[0]}) for matter {matter_id}")
        return {
            "id": row[0], "matter_id": row[1], "org_id": row[2], "created_by": row[3],
            "title": row[4], "participants": list(row[5] or []),
            "created_at": row[6].isoformat() if row[6] else None,
        }
    except Exception as e:
        write_log(f"create_matter_chat: Error - {e}")
        raise


def get_matter_chats_for_user(matter_id: int, user_id: str) -> list:
    """
    Return all chats for a matter that the user is a participant of.
    Results include participant count and last message preview.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                gc.id, gc.matter_id, gc.org_id, gc.created_by,
                gc.title, gc.participants, gc.created_at,
                (SELECT text FROM legal_saas.matter_chat_messages
                 WHERE chat_id = gc.id ORDER BY created_at DESC LIMIT 1) AS last_msg,
                (SELECT created_at FROM legal_saas.matter_chat_messages
                 WHERE chat_id = gc.id ORDER BY created_at DESC LIMIT 1) AS last_msg_at
            FROM legal_saas.matter_group_chats gc
            WHERE gc.matter_id = %s AND %s = ANY(gc.participants)
            ORDER BY COALESCE(
                (SELECT created_at FROM legal_saas.matter_chat_messages WHERE chat_id = gc.id ORDER BY created_at DESC LIMIT 1),
                gc.created_at
            ) DESC
            """,
            (matter_id, user_id)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "id": r[0], "matter_id": r[1], "org_id": r[2], "created_by": r[3],
                "title": r[4], "participants": list(r[5] or []),
                "created_at": r[6].isoformat() if r[6] else None,
                "last_message": r[7],
                "last_message_at": r[8].isoformat() if r[8] else None,
            }
            for r in rows
        ]
    except Exception as e:
        write_log(f"get_matter_chats_for_user: Error - {e}")
        return []


def get_matter_chat_messages(chat_id: int, limit: int = 100) -> list:
    """Fetch messages for a matter group chat, oldest first."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, sender_id, text, created_at
            FROM legal_saas.matter_chat_messages
            WHERE chat_id = %s
            ORDER BY created_at ASC
            LIMIT %s
            """,
            (chat_id, limit)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "id": r[0], "sender_id": r[1], "text": r[2],
                "created_at": r[3].isoformat() if r[3] else None
            }
            for r in rows
        ]
    except Exception as e:
        write_log(f"get_matter_chat_messages: Error - {e}")
        return []


def create_matter_chat_message(chat_id: int, sender_id: str, text: str) -> dict:
    """Insert a new message into a matter group chat."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO legal_saas.matter_chat_messages (chat_id, sender_id, text)
            VALUES (%s, %s, %s)
            RETURNING id, created_at
            """,
            (chat_id, sender_id, text)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return {
            "id": row[0], "chat_id": chat_id, "sender_id": sender_id,
            "text": text, "created_at": row[1].isoformat() if row[1] else None
        }
    except Exception as e:
        write_log(f"create_matter_chat_message: Error - {e}")
        raise


def get_matter_chat_by_id(chat_id: int) -> dict | None:
    """Fetch a single chat by its ID."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, matter_id, org_id, created_by, title, participants, created_at FROM legal_saas.matter_group_chats WHERE id = %s",
            (chat_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return None
        return {
            "id": row[0], "matter_id": row[1], "org_id": row[2], "created_by": row[3],
            "title": row[4], "participants": list(row[5] or []),
            "created_at": row[6].isoformat() if row[6] else None,
        }
    except Exception as e:
        write_log(f"get_matter_chat_by_id: Error - {e}")
        return None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id, participants, created_by, created_at FROM legal_saas.matter_group_chats WHERE matter_id = %s",
            (matter_id,)
        )
        row = cur.fetchone()

        if row:
            chat_id = row[0]
            existing = list(row[1] or [])
            merged = list(set(existing + participants))
            cur.execute(
                "UPDATE legal_saas.matter_group_chats SET participants = %s WHERE id = %s",
                (merged, chat_id)
            )
            conn.commit()
            write_log(f"get_or_create_matter_chat: Updated existing chat {chat_id} for matter {matter_id}")
        else:
            cur.execute(
                """
                INSERT INTO legal_saas.matter_group_chats (matter_id, org_id, created_by, participants)
                VALUES (%s, %s, %s, %s)
                RETURNING id, participants, created_by, created_at
                """,
                (matter_id, org_id, created_by, participants)
            )
            row = cur.fetchone()
            chat_id = row[0]
            conn.commit()
            write_log(f"get_or_create_matter_chat: Created new chat {chat_id} for matter {matter_id}")

        # Refetch final state
        cur.execute(
            "SELECT id, matter_id, org_id, created_by, participants, created_at FROM legal_saas.matter_group_chats WHERE id = %s",
            (chat_id,)
        )
        final = cur.fetchone()
        cur.close()
        conn.close()
        return {
            "id": final[0],
            "matter_id": final[1],
            "org_id": final[2],
            "created_by": final[3],
            "participants": list(final[4] or []),
            "created_at": final[5].isoformat() if final[5] else None,
        }
    except Exception as e:
        write_log(f"get_or_create_matter_chat: Error - {e}")
        raise


def get_matter_chat_messages(chat_id: int, limit: int = 100) -> list:
    """Fetch messages for a matter group chat, oldest first."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, sender_id, text, created_at
            FROM legal_saas.matter_chat_messages
            WHERE chat_id = %s
            ORDER BY created_at ASC
            LIMIT %s
            """,
            (chat_id, limit)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "id": r[0],
                "sender_id": r[1],
                "text": r[2],
                "created_at": r[3].isoformat() if r[3] else None
            }
            for r in rows
        ]
    except Exception as e:
        write_log(f"get_matter_chat_messages: Error - {e}")
        return []


def create_matter_chat_message(chat_id: int, sender_id: str, text: str) -> dict:
    """Insert a new message into a matter group chat."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO legal_saas.matter_chat_messages (chat_id, sender_id, text)
            VALUES (%s, %s, %s)
            RETURNING id, created_at
            """,
            (chat_id, sender_id, text)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return {
            "id": row[0],
            "chat_id": chat_id,
            "sender_id": sender_id,
            "text": text,
            "created_at": row[1].isoformat() if row[1] else None
        }
    except Exception as e:
        write_log(f"create_matter_chat_message: Error - {e}")
        raise


def get_matter_chat_by_matter(matter_id: int) -> dict | None:
    """Fetch existing group chat info for a matter (if any)."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, matter_id, org_id, created_by, participants, created_at FROM legal_saas.matter_group_chats WHERE matter_id = %s",
            (matter_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return None
        return {
            "id": row[0],
            "matter_id": row[1],
            "org_id": row[2],
            "created_by": row[3],
            "participants": list(row[4] or []),
            "created_at": row[5].isoformat() if row[5] else None,
        }
    except Exception as e:
        write_log(f"get_matter_chat_by_matter: Error - {e}")
        return None


# --- NOTIFICATIONS ---

def create_notification(user_id, title, message, notif_type, link=None):
    """Store a notification in the DB."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO legal_saas.notifications (user_id, title, message, type, link)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (user_id, title, message, notif_type, link)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return {
            "id": row[0],
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notif_type,
            "link": link,
            "read": False,
            "created_at": row[1].isoformat() if row[1] else None
        }
    except Exception as e:
        write_log(f"create_notification: Error - {e}")
        raise

def get_notifications(user_id, limit=50):
    """Fetch user notifications, newest first."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, title, message, type, link, read, created_at
            FROM legal_saas.notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, limit)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "id": r[0],
                "title": r[1],
                "message": r[2],
                "type": r[3],
                "link": r[4],
                "read": r[5],
                "created_at": r[6].isoformat() if r[6] else None
            }
            for r in rows
        ]
    except Exception as e:
        write_log(f"get_notifications: Error - {e}")
        return []

def mark_notifications_read(user_id):
    """Mark all notifications for a user as read."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE legal_saas.notifications SET read = TRUE WHERE user_id = %s",
            (user_id,)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        write_log(f"mark_notifications_read: Error - {e}")
        return False

def delete_notifications(user_id):
    """Clear all notifications for a user."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM legal_saas.notifications WHERE user_id = %s",
            (user_id,)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        write_log(f"delete_notifications: Error - {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# CORE FIELDS  (Super Admin managed)
# ─────────────────────────────────────────────────────────────────────────────

def get_all_core_fields():
    """Return every core field row."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, field_name, field_type, is_core, comments, created_at, updated_at
        FROM legal_saas.core_fields
        ORDER BY field_name ASC
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id": str(r[0]),
            "field_name": r[1],
            "field_type": r[2],
            "is_core": r[3],
            "comments": r[4],
            "created_at": r[5].isoformat() if r[5] else None,
            "updated_at": r[6].isoformat() if r[6] else None,
        }
        for r in rows
    ]


def create_core_field(field_name: str, field_type: str, is_core: bool = True, comments: str = ""):
    """Insert a new core field. Returns the new row."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO legal_saas.core_fields (field_name, field_type, is_core, comments)
        VALUES (%s, %s, %s, %s)
        RETURNING id, field_name, field_type, is_core, comments, created_at, updated_at
        """,
        (field_name, field_type, is_core, comments)
    )
    r = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return {
        "id": str(r[0]),
        "field_name": r[1],
        "field_type": r[2],
        "is_core": r[3],
        "comments": r[4],
        "created_at": r[5].isoformat() if r[5] else None,
        "updated_at": r[6].isoformat() if r[6] else None,
    }


def update_core_field(field_id: str, field_name: str, field_type: str, is_core: bool, comments: str):
    """Update an existing core field. Returns updated row or None."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE legal_saas.core_fields
        SET field_name = %s,
            field_type = %s,
            is_core    = %s,
            comments   = %s,
            updated_at = NOW()
        WHERE id = %s
        RETURNING id, field_name, field_type, is_core, comments, created_at, updated_at
        """,
        (field_name, field_type, is_core, comments, field_id)
    )
    r = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not r:
        return None
    return {
        "id": str(r[0]),
        "field_name": r[1],
        "field_type": r[2],
        "is_core": r[3],
        "comments": r[4],
        "created_at": r[5].isoformat() if r[5] else None,
        "updated_at": r[6].isoformat() if r[6] else None,
    }


def delete_core_field(field_id: str) -> bool:
    """Delete a core field by id."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM legal_saas.core_fields WHERE id = %s RETURNING id",
        (field_id,)
    )
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return deleted is not None


# ─────────────────────────────────────────────────────────────────────────────
# ORG CUSTOM FIELDS  (Admin adoption)
# ─────────────────────────────────────────────────────────────────────────────

def get_org_custom_fields(org_id: str):
    """
    Return all core fields together with whether this org has adopted them.
    Each row includes `adopted`, `is_required`, and `display_name` (org-level alias).
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT cf.id, cf.field_name, cf.field_type, cf.is_core, cf.comments,
               ocf.id      AS ocf_id,
               ocf.is_active,
               ocf.is_required,
               ocf.display_name
        FROM legal_saas.core_fields cf
        LEFT JOIN legal_saas.org_custom_fields ocf
               ON ocf.core_field_id = cf.id AND ocf.org_id = %s
        ORDER BY cf.field_name ASC
        """,
        (org_id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id": str(r[0]),
            "field_name": r[1],
            "field_type": r[2],
            "is_core": r[3],
            "comments": r[4],
            "adopted": r[5] is not None,
            "is_active": r[6] if r[6] is not None else False,
            "is_required": r[7] if r[7] is not None else False,
            "display_name": r[8] if r[8] is not None else "",
        }
        for r in rows
    ]


def adopt_core_field(org_id: str, core_field_id: str, is_required: bool = False, display_name: str = None):
    """Add a core field to an org's custom fields (or re-activate it). Optionally sets a display_name."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO legal_saas.org_custom_fields (org_id, core_field_id, is_active, is_required, display_name)
        VALUES (%s, %s, TRUE, %s, %s)
        ON CONFLICT (org_id, core_field_id)
        DO UPDATE SET is_active = TRUE,
                      is_required = EXCLUDED.is_required,
                      display_name = COALESCE(EXCLUDED.display_name, legal_saas.org_custom_fields.display_name),
                      updated_at = NOW()
        RETURNING id
        """,
        (org_id, core_field_id, is_required, display_name)
    )
    r = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return str(r[0]) if r else None


def update_org_field_display_name(org_id: str, core_field_id: str, display_name: str) -> bool:
    """Update the org-specific display name for an adopted field."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE legal_saas.org_custom_fields
        SET display_name = %s,
            updated_at = NOW()
        WHERE org_id = %s AND core_field_id = %s
        RETURNING id
        """,
        (display_name.strip() if display_name else None, org_id, core_field_id)
    )
    updated = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return updated is not None


def remove_org_custom_field(org_id: str, core_field_id: str) -> bool:
    """Remove (deactivate) a core field from an org."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM legal_saas.org_custom_fields
        WHERE org_id = %s AND core_field_id = %s
        RETURNING id
        """,
        (org_id, core_field_id)
    )
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return deleted is not None
