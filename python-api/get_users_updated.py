def get_users_by_org(clerk_org_id: str) -> list:
    """
    Fetch all users belonging to a specific organization with their teams.
    
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
            
        write_log(f"get_users_by_org: Found {len(users)} users")
        return users
        
    except Exception as e:
        write_log(f"get_users_by_org: Error - {e}")
        raise
