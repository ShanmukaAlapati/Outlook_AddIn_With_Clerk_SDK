"""
Route Logic for SaaS App
Determines which dashboard to redirect users to based on their role and permissions.
"""
from utils.logging_errors import write_log


def compute_redirect_url(auth_info: dict) -> str:
    """
    Decide which dashboard URL to send the user to,
    based on org_role (for now), but you can extend this later
    with org_slug, email, etc.
    
    Args:
        auth_info (dict): Authenticated user information containing:
            - org_role: User's role in organization
            - org_slug: Organization slug
            - email: User's email address
    
    Returns:
        str: Dashboard URL path to redirect user to
    """
    try:
        org_role = auth_info.get("org_role")
        org_slug = auth_info.get("org_slug")
        email = auth_info.get("email")
        
        write_log(f"compute_redirect_url: org_role={org_role}, org_slug={org_slug}, email={email}")

        # ----- SIMPLE ROLE-ONLY LOGIC FOR NOW -----
        # You can extend this later with org_slug/email-based rules.
        if org_role == "super-admin":
            write_log("compute_redirect_url: Redirecting to admin-dashboard")
            return "/admin-dashboard.html"

        if org_role == "org:admin":
            write_log("compute_redirect_url: Redirecting to org-dashboard (org:admin)")
            return "/org-dashboard.html"

        if isinstance(org_role, str) and org_role.startswith("org:"):
            write_log(f"compute_redirect_url: Redirecting to org-dashboard (role={org_role})")
            return "/org-dashboard.html"

        # Fallback: plain user
        write_log("compute_redirect_url: Redirecting to user-dashboard (default)")
        return "/user-dashboard.html"
        
    except Exception as e:
        write_log(f"compute_redirect_url: Error - {str(e)}, defaulting to user-dashboard")
        return "/user-dashboard.html"


# ==================================================================
# FUTURE ROUTING RULES (commented out for now)
# ==================================================================
# if org_slug == "acme" and org_role == "admin":
#     return f"/orgs/{org_slug}/admin.html"
#
# if email and email.endswith("@yourlawfirm.com"):
#     return "/partner-dashboard.html"
# ==================================================================
