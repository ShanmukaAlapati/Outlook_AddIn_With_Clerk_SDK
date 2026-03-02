"""
Team management functions for database.
"""
import psycopg2
from db_func import get_db_connection
from utils.logging_errors import write_log


def get_or_create_teams(clerk_org_id: str, team_names: list) -> list:
    """
    Get or create teams and return their IDs.
    
    Args:
        clerk_org_id (str): Organization ID
        team_names (list): List of team names
        
    Returns:
        list: List of team IDs
    """
    if not team_names:
        return []
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        team_ids = []
        for name in team_names:
            cur.execute(
                """
                INSERT INTO legal_saas.teams (clerk_org_id, name)
                VALUES (%s, %s)
                ON CONFLICT (clerk_org_id, name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                (clerk_org_id, name)
            )
            team_id = cur.fetchone()[0]
            team_ids.append(team_id)
        
        conn.commit()
        cur.close()
        conn.close()
        
        return team_ids
        
    except Exception as e:
        write_log(f"get_or_create_teams: Error - {e}")
        return []


def assign_user_to_teams(user_id: int, team_ids: list) -> bool:
    """
    Assign user to teams.
    
    Args:
        user_id (int): User ID
        team_ids (list): List of team IDs
        
    Returns:
        bool: Success status
    """
    if not team_ids:
        return True
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        for team_id in team_ids:
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
        
        return True
        
    except Exception as e:
        write_log(f"assign_user_to_teams: Error - {e}")
        return False


def get_user_teams(user_id: int) -> list:
    """
    Get team names for a user.
    
    Args:
        user_id (int): User ID
        
    Returns:
        list: List of team names
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT t.name FROM legal_saas.teams t
            JOIN legal_saas.user_teams ut ON t.id = ut.team_id
            WHERE ut.user_id = %s
            ORDER BY t.name
            """,
            (user_id,)
        )
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return [r[0] for r in rows]
        
    except Exception as e:
        write_log(f"get_user_teams: Error - {e}")
        return []
