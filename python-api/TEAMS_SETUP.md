# Teams Implementation Guide

## Step 1: Run Migration
```bash
python migrate_teams.py
```

This will:
- Create `legal_saas.teams` table
- Create `legal_saas.user_teams` junction table
- Drop the old `teams` column from users table

## Step 2: Update db_func.py

Replace the `create_local_user` function with the code from `create_local_user_updated.py`

Replace the `get_users_by_org` function with the code from `get_users_updated.py`

## Step 3: Update update_local_user_fields

Remove 'teams' from allowed_fields since teams are now managed via the junction table.

## Result

The API will now return team names instead of IDs:

```json
{
  "status": "success",
  "count": 2,
  "users": [
    {
      "id": 1,
      "clerk_user_id": "user_123",
      "email": "john@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "org:admin",
      "level": 3,
      "created_at": "2024-01-15T10:30:00",
      "teams": ["Backend", "DevOps"]
    }
  ]
}
```

The frontend will display these team names in the user details modal.
