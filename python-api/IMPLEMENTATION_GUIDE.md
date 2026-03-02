# Teams Implementation - Complete Fix Guide

## Problem Summary
Teams were not being saved to database because:
1. Frontend sends `team` (singular) but backend expects `teams` (plural array)
2. `create_local_user` wasn't saving teams to the junction table
3. `get_users_by_org` wasn't fetching team names

## Step 1: Run Database Migration
```bash
python migrate_teams.py
```

This creates:
- `legal_saas.teams` table
- `legal_saas.user_teams` junction table

## Step 2: Update Backend - db_func.py

Replace the `create_local_user` function with code from `create_local_user_correct.py`

This function now:
- Creates/updates user in users table
- Creates teams in teams table if they don't exist
- Links user to teams via user_teams junction table
- Logs all operations

## Step 3: Update Backend - db_func.py

Replace the `get_users_by_org` function with code from `get_users_updated.py`

This function now:
- JOINs users with user_teams and teams tables
- Returns team names (not IDs)
- Groups results properly

## Step 4: Update Frontend - app/admin/page.tsx

In `handleAddUser` function (around line 180):
```javascript
// CHANGE FROM:
teams: formData.team ? [formData.team] : []

// TO:
teams: formData.team ? [formData.team] : []
```

In `handleEditUser` function (around line 120):
```javascript
// CHANGE FROM:
team: teamValue || undefined

// TO:
teams: teamValue ? [teamValue] : []
```

## Data Flow

### Creating User:
1. Frontend sends: `{ email, teams: ['Backend', 'Frontend'] }`
2. Backend receives in create_clerk_user
3. Calls create_local_user with teams array
4. create_local_user:
   - Inserts user into users table
   - For each team name:
     - Inserts/gets team from teams table
     - Links user to team in user_teams table
5. Database now has:
   - users row
   - teams rows (if new)
   - user_teams rows linking them

### Retrieving Users:
1. Frontend calls GET /api/organization/{org_id}/users
2. Backend calls get_users_by_org
3. get_users_by_org:
   - JOINs users → user_teams → teams
   - Groups by user
   - Aggregates team names into array
4. Returns: `{ teams: ['Backend', 'Frontend'] }`
5. Frontend displays in modal

## Verification

After implementation, when you:
1. Create a user with teams
2. Check database:
   ```sql
   SELECT u.email, array_agg(t.name) as teams
   FROM legal_saas.users u
   LEFT JOIN legal_saas.user_teams ut ON u.id = ut.user_id
   LEFT JOIN legal_saas.teams t ON ut.team_id = t.id
   GROUP BY u.id, u.email;
   ```
3. Should see teams listed for each user

## Files to Update

1. `db_func.py` - Replace `create_local_user` and `get_users_by_org`
2. `app/admin/page.tsx` - Change `team` to `teams` in two places
3. Run `migrate_teams.py` once to create tables
