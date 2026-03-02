def create_local_user(user_data: dict) -> dict:
    """
    Create or update a user and assign teams to database.
    
    Args:
        user_data (dict): {
            "clerk_user_id": str,
            "email": str,
            "first_name": str,
            "last_name": str,
            "role": str,
            "level": int,
            "clerk_org_id": str,
            "teams": list of team names ['Backend', 'Frontend']
        }
    
    Returns:
        dict: {"success": bool, "id": int, "message": str}
    """
    try:
        write_log(f"create_local_user: Saving user {user_data.get('email')} with teams={user_data.get('teams')}")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        clerk_user_id = user_data['clerk_user_id']
        clerk_org_id = user_data.get('clerk_org_id')
        teams = user_data.get('teams', [])
        
        # Check if user exists
        cur.execute(
            "SELECT id FROM legal_saas.users WHERE clerk_user_id = %s",
            (clerk_user_id,)
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
                    clerk_org_id,
                    user_id
                )
            )
            action = "updated"
            # Clear existing teams
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
                    clerk_user_id,
                    user_data['email'],
                    user_data.get('first_name'),
                    user_data.get('last_name'),
                    user_data.get('role'),
                    user_data.get('level'),
                    clerk_org_id
                )
            )
            user_id = cur.fetchone()[0]
            action = "created"
        
        # Assign teams
        if teams and clerk_org_id:
            for team_name in teams:
                # Get or create team
                cur.execute(
                    """
                    INSERT INTO legal_saas.teams (clerk_org_id, name)
                    VALUES (%s, %s)
                    ON CONFLICT (clerk_org_id, name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                    (clerk_org_id, team_name)
                )
                team_id = cur.fetchone()[0]
                
                # Assign user to team
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
