# clerk_client.py
"""
Clerk API client for organization management.
Handles organization creation and membership management.
"""
import os
from clerk_backend_api import Clerk
from utils.logging_errors import write_log
from dotenv import load_dotenv

load_dotenv()

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
SUPER_ADMIN = os.getenv("SUPER_ADMIN")
SUPER_ADMIN_CLERK_USER_ID = os.getenv("SUPER_ADMIN_CLERK_USER_ID")

if not SUPER_ADMIN:
    msg = "SUPER_ADMIN is not set in environment"
    write_log(msg)
    raise RuntimeError(msg)

if not SUPER_ADMIN_CLERK_USER_ID:
    msg = "SUPER_ADMIN_CLERK_USER_ID is not set in environment"
    write_log(msg)
    raise RuntimeError(msg)

if not CLERK_SECRET_KEY:
    msg = "CLERK_SECRET_KEY is not set in environment"
    write_log(msg)
    raise RuntimeError(msg)  # ✅ Fail early if key is missing


def check_clerk_user_exists(email: str) -> bool:
    """Check if a user with the given email already exists in Clerk."""
    if not CLERK_SECRET_KEY:
        raise RuntimeError("CLERK_SECRET_KEY not configured")
    
    with Clerk(bearer_auth=CLERK_SECRET_KEY) as clerk:
        try:
            users = clerk.users.list(request={"email_address": [email]})
            return len(users) > 0
        except Exception as e:
            write_log(f"check_clerk_user_exists: Error checking email {email} - {e}")
            return False


def create_clerk_org(org_name: str, slug: str | None, admin_user_id: str, number_of_seats: int, signup_email: str):
    """
    Create a new organization in Clerk and add admin as member.

    admin_user_id MUST be a Clerk user ID (user_...), not email.
    """
    if not CLERK_SECRET_KEY:
        msg = "create_clerk_org called without CLERK_SECRET_KEY configured"
        write_log(msg)
        raise RuntimeError(msg)

    try:
        write_log(f"create_clerk_org: Creating org '{org_name}' for admin {admin_user_id}")

        with Clerk(bearer_auth=CLERK_SECRET_KEY) as clerk:
            # Pass parameters via 'request' dictionary as per SDK signature
            org = clerk.organizations.create(request={
                "name": org_name,
                "slug": slug,
                "created_by": admin_user_id,
                "max_allowed_memberships": number_of_seats,
                "public_metadata": {
                    "created_via": "admin_approval",
                    "signup_email": signup_email,
                    "admin_user_id": admin_user_id,
                }
            })

            write_log(
                f"create_clerk_org: ✓ Organization created - id={org.id}, slug={org.slug}, name={org.name}"
            )
            return org

    except Exception as e:
        error_msg = str(e)
        write_log(f"create_clerk_org: Error details - {error_msg}")
        
        # Check if it's a parameter error
        if "unexpected keyword argument" in error_msg:
            write_log(f"create_clerk_org: Trying alternative API call without problematic parameters")
            try:
                with Clerk(bearer_auth=CLERK_SECRET_KEY) as clerk:
                    # Try with minimal parameters via request dict
                    org = clerk.organizations.create(request={
                        "name": org_name,
                        "created_by": admin_user_id,
                    })
                    write_log(f"create_clerk_org: ✓ Organization created with minimal params - id={org.id}")
                    return org
            except Exception as inner_e:
                write_log(f"create_clerk_org: Alternative API call also failed - {inner_e}")
                raise Exception(f"Failed to create Clerk organization: {str(inner_e)}")
        
        # Check if slug already exists
        is_slug_taken = False
        if hasattr(e, "data") and hasattr(e.data, "errors"):
            for err in e.data.errors:
                if getattr(err, "code", "") == "form_identifier_exists":
                    is_slug_taken = True
                    break
        
        if not is_slug_taken and "form_identifier_exists" in str(e):
             is_slug_taken = True
        
        if is_slug_taken:
            write_log(f"create_clerk_org: Org with slug '{slug}' already exists (unexpected collision).")
            raise Exception(f"Failed to create Clerk organization: Slug '{slug}' already exists and fallback is disabled.")

        write_log(f"create_clerk_org: ✗ Error creating organization - {e}")
        raise Exception(f"Failed to create Clerk organization: {str(e)}")


def get_clerk_organization(org_id: str):
    """
    Fetch organization details from Clerk by ID.
    
    What it does:
    - Retrieves organization information from Clerk
    - Returns full organization object with all metadata
    
    Args:
        org_id: Clerk organization ID (e.g., "org_2xxx...")
    
    Returns:
        Organization object
    """
    if not CLERK_SECRET_KEY:
        raise RuntimeError("CLERK_SECRET_KEY not configured")
    
    try:
        with Clerk(bearer_auth=CLERK_SECRET_KEY) as clerk:
            org = clerk.organizations.get(organization_id=org_id)
            write_log(f"get_clerk_organization: Fetched org {org_id}")
            return org
    except Exception as e:
        write_log(f"get_clerk_organization: Error fetching org {org_id} - {e}")
        raise


def update_clerk_organization(org_id: str, **kwargs):
    """
    Update organization details in Clerk.
    
    What it does:
    - Updates organization fields (name, slug, metadata, etc.)
    - Returns updated organization object
    
    Args:
        org_id: Clerk organization ID
        **kwargs: Fields to update (name, slug, public_metadata, private_metadata, etc.)
    
    Returns:
        Updated organization object
    """
    if not CLERK_SECRET_KEY:
        raise RuntimeError("CLERK_SECRET_KEY not configured")
    
    try:
        with Clerk(bearer_auth=CLERK_SECRET_KEY) as clerk:
            org = clerk.organizations.update(
                organization_id=org_id,
                **kwargs
            )
            write_log(f"update_clerk_organization: Updated org {org_id}")
            return org
    except Exception as e:
        write_log(f"update_clerk_organization: Error updating org {org_id} - {e}")
        raise


def delete_clerk_organization(org_id: str):
    """
    Delete organization from Clerk.
    
    What it does:
    - Permanently deletes organization and all associated memberships
    - Cannot be undone
    
    Args:
        org_id: Clerk organization ID
    """
    if not CLERK_SECRET_KEY:
        raise RuntimeError("CLERK_SECRET_KEY not configured")
    
    try:
        with Clerk(bearer_auth=CLERK_SECRET_KEY) as clerk:
            clerk.organizations.delete(organization_id=org_id)
            write_log(f"delete_clerk_organization: Deleted org {org_id}")
    except Exception as e:
        write_log(f"delete_clerk_organization: Error deleting org {org_id} - {e}")
        raise


def delete_clerk_user(user_id: str) -> bool:
    """
    Permanently delete a Clerk user by their Clerk user ID.

    Args:
        user_id: Clerk user ID (e.g. 'user_2xxx...')

    Returns:
        True on success, False if user was not found (already deleted).
    """
    if not CLERK_SECRET_KEY:
        raise RuntimeError("CLERK_SECRET_KEY not configured")

    try:
        with Clerk(bearer_auth=CLERK_SECRET_KEY) as clerk:
            clerk.users.delete(user_id=user_id)
            write_log(f"delete_clerk_user: Deleted Clerk user {user_id}")
            return True
    except Exception as e:
        err_str = str(e)
        # If user is already gone, treat as idempotent success
        if "not_found" in err_str.lower() or "404" in err_str:
            write_log(f"delete_clerk_user: User {user_id} already deleted (not found in Clerk)")
            return False
        write_log(f"delete_clerk_user: Error deleting Clerk user {user_id} - {e}")
        raise


def add_organization_member(org_id: str, user_id: str, role: str = "org:member"):
    """
    Add a user to an organization with specified role.
    
    What it does:
    - Creates organization membership for the user
    - Assigns specified role (member or admin)
    - User gains access to organization resources
    
    Args:
        org_id: Clerk organization ID
        user_id: Clerk user ID to add
        role: Role to assign - "org:member" or "org:admin" (default: "org:member")
    
    Returns:
        Membership object
    """
    if not CLERK_SECRET_KEY:
        raise RuntimeError("CLERK_SECRET_KEY not configured")
    
    try:
        with Clerk(bearer_auth=CLERK_SECRET_KEY) as clerk:
            membership = clerk.organization_memberships.create(
                organization_id=org_id,
                user_id=user_id,
                role=role
            )
            write_log(f"add_organization_member: Added user {user_id} to org {org_id} with role {role}")
            return membership
    except Exception as e:
        # Check if user is already a member
        is_already_member = False
        if hasattr(e, "data") and hasattr(e.data, "errors"):
            for err in e.data.errors:
                if getattr(err, "code", "") == "already_a_member_in_organization":
                    is_already_member = True
                    break
        
        if not is_already_member and "already_a_member_in_organization" in str(e):
             is_already_member = True

        if is_already_member:
            write_log(f"add_organization_member: User {user_id} is already a member of org {org_id} (idempotent success)")
            return None

        write_log(f"add_organization_member: Error adding user {user_id} to org {org_id} - {e}")
        raise


def remove_organization_member(org_id: str, user_id: str):
    """
    Remove a user from an organization.
    
    What it does:
    - Deletes organization membership
    - User loses access to organization resources
    
    Args:
        org_id: Clerk organization ID
        user_id: Clerk user ID to remove
    """
    if not CLERK_SECRET_KEY:
        raise RuntimeError("CLERK_SECRET_KEY not configured")
    
    try:
        with Clerk(bearer_auth=CLERK_SECRET_KEY) as clerk:
            clerk.organization_memberships.delete(
                organization_id=org_id,
                user_id=user_id
            )
            write_log(f"remove_organization_member: Removed user {user_id} from org {org_id}")
    except Exception as e:
        write_log(f"remove_organization_member: Error removing user {user_id} from org {org_id} - {e}")
        raise


def list_organization_members(org_id: str, limit: int = 100):
    """
    List all members of an organization.
    
    What it does:
    - Retrieves all memberships for the organization
    - Returns list with user details and roles
    
    Args:
        org_id: Clerk organization ID
        limit: Maximum number of results to return (default: 100)
    
    Returns:
        List of membership objects
    """
    if not CLERK_SECRET_KEY:
        raise RuntimeError("CLERK_SECRET_KEY not configured")
    
    try:
        with Clerk(bearer_auth=CLERK_SECRET_KEY) as clerk:
            memberships = clerk.organization_memberships.list(
                organization_id=org_id,
                limit=limit
            )
            write_log(f"list_organization_members: Listed members for org {org_id}")
            return memberships.data if hasattr(memberships, 'data') else memberships
    except Exception as e:
        write_log(f"list_organization_members: Error listing members for org {org_id} - {e}")
        raise


# ------------- NEW: ensure Clerk user for signup email -------------

def get_or_create_clerk_user(email: str, first_name: str | None = None, last_name: str | None = None, level: int | None = None, teams: list[str] | None = None, password: str | None = None, password_digest: str | None = None, password_hasher: str | None = None):
    """
    Ensure there's a Clerk user for this email.
    Returns Clerk user object.
    
    If level is provided, it is stored in public_metadata.
    If teams is provided, it is stored in public_metadata.
    If password is provided, it is used to create the user with password authentication.
    """
    if not CLERK_SECRET_KEY:
        raise RuntimeError("CLERK_SECRET_KEY not configured")

    with Clerk(bearer_auth=CLERK_SECRET_KEY) as clerk:
        try:
            # users.list returns a List[User] directly, not an object with .data
            # Pass parameters via 'request' dictionary as per SDK signature
            users = clerk.users.list(request={"email_address": [email]})
        except Exception as e:
            write_log(f"get_or_create_clerk_user: Error listing users for {email}: {e}")
            users = None

        if users and len(users) > 0:
            user = users[0]
            write_log(f"get_or_create_clerk_user: Found existing user {user.id} for {email}")

            # If a new password was supplied (e.g. re-registration after org deletion,
            # or admin adding user with explicit password), update it in Clerk so
            # the user can log in with the new credentials.
            if password_digest or password:
                try:
                    if password_digest:
                        clerk.users.update(
                            user_id=user.id,
                            password_digest=password_digest,
                            password_hasher=password_hasher or "bcrypt",
                            skip_password_checks=False,
                        )
                    elif password:
                        clerk.users.update(
                            user_id=user.id,
                            password=password,
                            skip_password_checks=False,
                        )
                    write_log(
                        f"get_or_create_clerk_user: Updated password for existing user {user.id} ({email})"
                    )
                except Exception as pw_err:
                    write_log(
                        f"get_or_create_clerk_user: ERROR — could not update password for {user.id}: {pw_err}"
                    )
                    raise RuntimeError(f"Failed to set password for existing user {email}: {pw_err}")

            # Update level / teams metadata if provided
            if level is not None:
                try:
                    current_metadata = user.public_metadata or {}
                    should_update = False
                    if current_metadata.get("level") != level:
                        write_log(f"get_or_create_clerk_user: Updating user {user.id} level to {level}")
                        current_metadata["level"] = level
                        should_update = True
                    
                    if teams is not None and current_metadata.get("teams") != teams:
                        write_log(f"get_or_create_clerk_user: Updating user {user.id} teams to {teams}")
                        current_metadata["teams"] = teams
                        should_update = True

                    if should_update:
                        clerk.users.update(
                            user_id=user.id,
                            public_metadata=current_metadata
                        )
                except Exception as e:
                    write_log(f"get_or_create_clerk_user: Error updating user metadata: {e}")
            
            return user

        try:
            public_metadata = {}
            if level is not None:
                public_metadata["level"] = level
            if teams is not None:
                public_metadata["teams"] = teams

            # Determine password requirements based on whether password or digest is provided
            skip_checks = True
            if password or password_digest:
                skip_checks = False

            user = clerk.users.create(
                email_address=[email],
                first_name=first_name,
                last_name=last_name,
                password=password,
                password_digest=password_digest,
                password_hasher=password_hasher,
                skip_password_checks=skip_checks,
                skip_password_requirement=skip_checks,
                public_metadata=public_metadata
            )
            write_log(f"get_or_create_clerk_user: Created new user {user.id} for {email} with level {level} and teams {teams} (password set: {bool(password or password_digest)})")
            return user
        except Exception as e:
            # Check for ClerkErrors and specific error code
            is_existing_user_error = False
            if hasattr(e, "data") and hasattr(e.data, "errors"):
                for err in e.data.errors:
                    if getattr(err, "code", "") == "form_identifier_exists":
                        is_existing_user_error = True
                        break
            
            # Fallback to string check if structure is different
            if not is_existing_user_error and "form_identifier_exists" in str(e):
                is_existing_user_error = True

            if is_existing_user_error:
                write_log(f"get_or_create_clerk_user: User {email} already exists during create, fetching...")
                users = clerk.users.list(request={"email_address": [email]})
                if users and len(users) > 0:
                    user = users[0]
                    # Update level if provided (handling race condition where user was created just now)
                    try:
                        current_metadata = user.public_metadata or {}
                        should_update = False
                        
                        if level is not None and current_metadata.get("level") != level:
                            current_metadata["level"] = level
                            should_update = True
                            
                        if teams is not None and current_metadata.get("teams") != teams:
                            current_metadata["teams"] = teams
                            should_update = True
                            
                        if should_update:
                            clerk.users.update(
                                user_id=user.id,
                                public_metadata=current_metadata
                            )
                    except Exception as inner_e:
                        write_log(f"get_or_create_clerk_user: Error updating metadata after race-condition fetch: {inner_e}")
                    return user
            
            write_log(f"get_or_create_clerk_user: Error creating user {email}: {e}")
            raise e


def update_clerk_user_level(user_id: str, level: int):
    """
    Update the user's level in Clerk public_metadata.
    """
    if not CLERK_SECRET_KEY:
        raise RuntimeError("CLERK_SECRET_KEY not configured")
    
    try:
        with Clerk(bearer_auth=CLERK_SECRET_KEY) as clerk:
            # Fetch user to get existing metadata
            user = clerk.users.get(user_id=user_id)
            current_metadata = user.public_metadata or {}
            
            # Update
            clerk.users.update(
                user_id=user_id,
                public_metadata={**current_metadata, "level": level}
            )
            write_log(f"update_clerk_user_level: Updated user {user_id} level to {level}")
            
    except Exception as e:
        write_log(f"update_clerk_user_level: Error - {e}")
        raise


def update_org_membership_role(org_id: str, user_id: str, role: str):
    """
    Update a user's role within an organization.
    Role should be "org:admin" or "org:member".
    """
    if not CLERK_SECRET_KEY:
        raise RuntimeError("CLERK_SECRET_KEY not configured")
    
    try:
        with Clerk(bearer_auth=CLERK_SECRET_KEY) as clerk:
            clerk.organization_memberships.update(
                organization_id=org_id,
                user_id=user_id,
                role=role
            )
            write_log(f"update_org_membership_role: Updated user {user_id} role to {role} in org {org_id}")
            
    except Exception as e:
        write_log(f"update_org_membership_role: Error - {e}")
        raise









