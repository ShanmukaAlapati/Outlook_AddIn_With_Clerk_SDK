# approve_signup_service.py
from clerk_backend_api import Clerk
from utils.logging_errors import write_log
from db_func import get_signup_by_id
from db_func import get_db_connection, get_signup_by_id, create_local_user
from clerk_client import (
    CLERK_SECRET_KEY,
    SUPER_ADMIN,
    SUPER_ADMIN_CLERK_USER_ID,
    create_clerk_org,
    add_organization_member,
    get_or_create_clerk_user,
)
import bcrypt
import time


def _get_signup_row(signup_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, organization_name, email, status, clerk_user_id, password_hash
            FROM legal_saas.org_signups
            WHERE id = %s
            """,
            (signup_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        write_log(f"_get_signup_row: fetched row for id={signup_id}: {row}")
        return row
    except Exception as e:
        write_log(f"_get_signup_row ERROR id={signup_id}: {e}")
        return None


def _ensure_clerk_columns():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            ALTER TABLE legal_saas.org_signups
            ADD COLUMN IF NOT EXISTS clerk_org_id VARCHAR(100),
            ADD COLUMN IF NOT EXISTS clerk_org_slug VARCHAR(200);
            """
        )
        conn.commit()
        cur.close()
        conn.close()
        write_log("_ensure_clerk_columns: columns ensured")
    except Exception as e:
        write_log(f"_ensure_clerk_columns ERROR: {e}")
        raise


def _update_signup_as_approved(signup_id, org_id, org_slug):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE legal_saas.org_signups
            SET status = 'approved',
                clerk_org_id = %s,
                clerk_org_slug = %s
            WHERE id = %s
            """,
            (org_id, org_slug, signup_id),
        )
        conn.commit()
        cur.close()
        conn.close()
        write_log(
            f"_update_signup_as_approved: id={signup_id}, org_id={org_id}, org_slug={org_slug}"
        )
    except Exception as e:
        write_log(
            f"_update_signup_as_approved ERROR id={signup_id}, org_id={org_id}, org_slug={org_slug}: {e}"
        )
        raise

def approve_signup_service(signup_id: int):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        write_log(f"approve_signup_service: Approving signup {signup_id}")

        # 1) Load signup row
        signup = get_signup_by_id(signup_id)
        if not signup:
            return {"error": "Signup not found"}, 404

        org_name = signup["organization_name"]
        admin_name = signup["admin_name"]
        email = signup["email"]
        number_of_seats = signup["number_of_seats"]
        clerk_org_id = signup.get("clerk_org_id")
        existing_admin_user_id = signup.get("clerk_user_id")
        password_hash = signup.get("password_hash")

        write_log(
            f"approve_signup_service: signup loaded email={email}, org_name={org_name}, clerk_org_id={clerk_org_id}, clerk_user_id={existing_admin_user_id}"
        )

        first_name = admin_name.strip().split(" ")[0] if admin_name else None
        last_name = (
            " ".join(admin_name.strip().split(" ")[1:])
            if admin_name and " " in admin_name
            else None
        )

        if not CLERK_SECRET_KEY:
            raise RuntimeError("CLERK_SECRET_KEY not configured")

        # 2) Ensure Clerk org exists (or create with signup admin as creator)
        with Clerk(bearer_auth=CLERK_SECRET_KEY) as clerk:
            if clerk_org_id:
                org = clerk.organizations.get(organization_id=clerk_org_id)
                write_log(
                    f"approve_signup_service: Using existing org {clerk_org_id} from signup row"
                )
            else:
                slug = f"{org_name.lower().replace(' ', '-')}-{signup_id}"

                # 2a) Ensure Clerk user exists for signup email (this will be org admin)
                if existing_admin_user_id:
                     admin_user_id = existing_admin_user_id
                     write_log(f"approve_signup_service: Using existing admin user {admin_user_id}")
                     # Optionally fetch the user object if needed, but ID is enough for org creation
                     try:
                         admin_user = clerk.users.get(user_id=admin_user_id)
                     except Exception:
                         write_log(f"approve_signup_service: Could not fetch user object for {admin_user_id}, proceeding with ID")
                         admin_user = type('obj', (object,), {'id': admin_user_id})
                else:
                    admin_user = get_or_create_clerk_user(
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        password_digest=password_hash,
                        password_hasher="bcrypt"
                    )
                    admin_user_id = admin_user.id

                write_log(
                    f"approve_signup_service: Creating new org with created_by={admin_user_id} for email={email}"
                )

                # 2b) Create org with created_by = admin_user_id
                org = create_clerk_org(
                    org_name=org_name,
                    slug=slug,
                    admin_user_id=admin_user_id,
                    number_of_seats=number_of_seats,
                    signup_email=email,
                )

                clerk_org_id = org.id
                write_log(
                    f"approve_signup_service: Created new org {clerk_org_id} for signup {signup_id}"
                )

            # If org already existed and we skipped the new-user path, we still need admin_user
            if not clerk_org_id:
                clerk_org_id = org.id
            if "admin_user" not in locals():
                admin_user = get_or_create_clerk_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                )

            # 3) Add that user as org:admin (idempotent if already member)
            add_organization_member(
                org_id=clerk_org_id,
                user_id=admin_user.id,
                role="org:admin",
            )

        # 4) Create local user record
        create_local_user({
            "clerk_user_id": admin_user.id,      # from Clerk user
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "role": "org:admin",                 # your business role
            "level": 1,                          # or whatever int level you use
            "clerk_org_id": clerk_org_id,        # org id from Clerk
            "teams": ["org:admin"],              # list of team names (strings)
        })

        # 5) Update signup DB row
        cur.execute(
            """
            UPDATE legal_saas.org_signups
            SET status = %s,
                approved_at = NOW(),
                clerk_org_id = %s
            WHERE id = %s
            """,
            ("approved", clerk_org_id, signup_id),
        )
        conn.commit()

        result = {
            "status": "approved",
            "signup_id": signup_id,
            "clerk_org_id": clerk_org_id,
            "org_name": org_name,
            "admin_email": email,
            "admin_user_id": admin_user.id,
            "number_of_seats": number_of_seats,
        }
        write_log(f"approve_signup_service: Success {result}")
        return result, 200

    except Exception as e:
        conn.rollback()
        write_log(
            f"approve_signup_service: Error approving signup {signup_id} - {e}"
        )
        return {"error": str(e)}, 500

    finally:
        cur.close()
        conn.close()
def create_organization_direct_service(data: dict):
    """
    Directly create an organization and admin user (Super Admin bypass).
    data: {
        "organization_name": str,
        "admin_name": str,
        "email": str,
        "number_of_seats": int
    }
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        org_name = data.get("organization_name")
        admin_name = data.get("admin_name")
        email = data.get("email")
        password = data.get("password")
        number_of_seats = data.get("number_of_seats", 5)

        if not org_name or not admin_name or not email or not password:
            return {"error": "Missing required fields (including password)"}, 400

        write_log(f"create_organization_direct_service: Creating org={org_name} for email={email}")

        # Hash password for Clerk/DB consistency
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        first_name = admin_name.strip().split(" ")[0] if admin_name else None
        last_name = (
            " ".join(admin_name.strip().split(" ")[1:])
            if admin_name and " " in admin_name
            else None
        )

        if not CLERK_SECRET_KEY:
            raise RuntimeError("CLERK_SECRET_KEY not configured")

        # 1) Generate unique ID and Insert into org_signups as 'approved'
        signup_id = int(time.time() * 1000)
        cur.execute(
            """
            INSERT INTO legal_saas.org_signups 
            (id, organization_name, admin_name, email, number_of_seats, status, created_at, approved_at, password_hash)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW(), %s)
            RETURNING id
            """,
            (signup_id, org_name, admin_name, email, number_of_seats, "approved", hashed_password),
        )
        signup_id = cur.fetchone()[0]

        # 2) Clerk creation logic
        with Clerk(bearer_auth=CLERK_SECRET_KEY) as clerk:
            # 2a) Ensure Clerk user exists
            admin_user = get_or_create_clerk_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                password_digest=hashed_password,
                password_hasher="bcrypt"
            )
            admin_user_id = admin_user.id
            write_log(f"create_organization_direct_service: Admin user ID={admin_user_id}")

            # 2b) Create Clerk organization
            slug = f"{org_name.lower().replace(' ', '-')}-{signup_id}"
            org = create_clerk_org(
                org_name=org_name,
                slug=slug,
                admin_user_id=admin_user_id,
                number_of_seats=number_of_seats,
                signup_email=email,
            )
            clerk_org_id = org.id
            write_log(f"create_organization_direct_service: Created org {clerk_org_id}")

            # 2c) Add user as org:admin
            add_organization_member(
                org_id=clerk_org_id,
                user_id=admin_user_id,
                role="org:admin",
            )

        # 3) Create local user record
        create_local_user({
            "clerk_user_id": admin_user_id,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "role": "org:admin",
            "level": 1,
            "clerk_org_id": clerk_org_id,
            "teams": ["org:admin"],
        })

        # 4) Update signup record with Clerk Org ID and user ID
        cur.execute(
            """
            UPDATE legal_saas.org_signups
            SET clerk_org_id = %s,
                clerk_user_id = %s
            WHERE id = %s
            """,
            (clerk_org_id, admin_user_id, signup_id),
        )
        conn.commit()

        result = {
            "status": "success",
            "message": "Organization created and approved successfully",
            "signup_id": signup_id,
            "clerk_org_id": clerk_org_id,
            "org_name": org_name,
            "admin_email": email
        }
        write_log(f"create_organization_direct_service: Success {result}")
        return result, 201

    except Exception as e:
        conn.rollback()
        write_log(f"create_organization_direct_service: Error - {e}")
        return {"error": str(e)}, 500
    finally:
        cur.close()
        conn.close()
