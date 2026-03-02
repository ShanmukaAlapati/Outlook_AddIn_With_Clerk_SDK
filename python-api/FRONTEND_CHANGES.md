// CHANGES NEEDED IN admin/page.tsx

// 1. In handleAddUser function, change this:
// OLD:
body: JSON.stringify({
  token,
  email: formData.email,
  password: formData.password,
  firstName: formData.name.split(' ')[0],
  lastName: formData.name.split(' ').slice(1).join(' '),
  level: formData.level ? parseInt(formData.level) : undefined,
  team: formData.team || undefined  // WRONG - singular
})

// NEW:
body: JSON.stringify({
  token,
  email: formData.email,
  password: formData.password,
  firstName: formData.name.split(' ')[0],
  lastName: formData.name.split(' ').slice(1).join(' '),
  level: formData.level ? parseInt(formData.level) : undefined,
  teams: formData.team ? [formData.team] : []  // CORRECT - plural array
})

// 2. In handleEditUser function, change this:
// OLD:
await api.patch(
  `/api/users/${currentUser.id}`,
  {
    org_id: organization.id,
    level: parseInt(levelValue.replace('L', '')),
    team: teamValue || undefined  // WRONG - singular
  },
  token
)

// NEW:
await api.patch(
  `/api/users/${currentUser.id}`,
  {
    org_id: organization.id,
    level: parseInt(levelValue.replace('L', '')),
    teams: teamValue ? [teamValue] : []  // CORRECT - plural array
  },
  token
)
