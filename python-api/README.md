# Case Counsil - Legal SaaS Platform

A multi-tenant B2B SaaS platform for legal case management with organization-based access control, built with Next.js (frontend) and Flask (backend).

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [User Roles & Permissions](#user-roles--permissions)
- [API Endpoints](#api-endpoints)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

Case Counsil is an enterprise-grade legal case management platform that allows organizations to manage their legal workflows. The platform features a multi-tenant architecture where each organization has isolated data and user management.

### Key Workflows

1. **Organization Signup** → Admin submits organization registration
2. **Super Admin Approval** → Platform admin reviews and approves/rejects
3. **Organization Creation** → Clerk organization created upon approval
4. **User Access** → Approved admins and members access their dashboards

---

## ✨ Features

### Authentication & Authorization

- 🔐 Clerk-based authentication with JWT verification
- 👥 Multi-tenant organization management
- 🎭 Role-based access control (Super Admin, Org Admin, Org Member)
- 🔑 Secure password hashing with bcrypt

### Organization Management

- 📝 Organization signup with approval workflow
- ✅ Super admin approval/rejection system
- 🏢 Automatic Clerk organization creation
- 👤 Seat-based user management

### Security Features

- 🛡️ Rate limiting to prevent abuse
- 🔒 CORS protection with configurable origins
- 🔐 JWT token verification with JWKS
- 🚫 SQL injection prevention with parameterized queries
- 🧹 Input sanitization and validation

### Database

- 💾 PostgreSQL database with proper indexing
- 📊 Signup tracking with status management
- 🔍 Audit trail (created_at, approved_at, rejected_at)

---

## 🛠 Tech Stack

### Frontend

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Authentication:** Clerk React SDK
- **Styling:** Tailwind CSS
- **HTTP Client:** Fetch API

### Backend

- **Framework:** Flask 3.0
- **Language:** Python 3.9+
- **Authentication:** Clerk Backend API, PyJWT
- **Database:** PostgreSQL (via psycopg2)
- **Security:** bcrypt, Flask-CORS, Flask-Limiter

### Infrastructure

- **Frontend Hosting:** Vercel / Netlify
- **Backend Hosting:** Render / Heroku
- **Database:** Render PostgreSQL / AWS RDS
- **Authentication:** Clerk.dev

---

## 🏗 Architecture

┌─────────────────────────────────────────────────────────────┐
│ Frontend (Next.js) │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│ │ Sign Up │ │ Sign In │ │ Admin │ │ User │ │
│ │ Page │ │ Page │ │Dashboard │ │Dashboard │ │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│ ↓ HTTP/HTTPS ↓ │
└─────────────────────────────────────────────────────────────┘
↓
┌─────────────────────────────────────────────────────────────┐
│ Backend (Flask) │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│ │ Auth Service │ │ Signup Service│ │Approval Service│ │
│ │ (JWT Verify) │ │ (Register) │ │ (Clerk Org) │ │
│ └──────────────┘ └──────────────┘ └──────────────┘ │
│ ↓ │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Database Functions (db_func.py) │ │
│ └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
↓
┌─────────────────────────────────────────────────────────────┐
│ PostgreSQL Database │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ legal_saas.org_signups │ │
│ │ - Signup requests │ │
│ │ - Organization details │ │
│ │ - Approval status │ │
│ └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
↓
┌─────────────────────────────────────────────────────────────┐
│ Clerk (Authentication) │
│ - User Management │
│ - Organization Management │
│ - JWT Token Issuance │
└─────────────────────────────────────────────────────────────┘

---

## 📋 Prerequisites

### Required Software

- **Python:** 3.9 or higher
- **Node.js:** 18.x or higher
- **npm/yarn:** Latest version
- **PostgreSQL:** 13 or higher

### Required Accounts

- **Clerk Account:** [Sign up at clerk.dev](https://clerk.dev)
- **PostgreSQL Database:** Local or hosted (Render, AWS RDS, etc.)

---

## 📦 Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/case-counsil.git
cd case-counsil

2. Backend Setup
bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
3. Frontend Setup
bash
# Navigate to frontend directory
cd UI

# Install dependencies
npm install
# or
yarn install
⚙️ Configuration
Backend Environment Variables
Create .env file in the root directory:

bash
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-change-in-production

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/case_counsil

# Clerk Configuration
CLERK_SECRET_KEY=sk_test_your_clerk_secret_key

# Super Admin Configuration
SUPER_ADMIN_EMAILS=admin@yourcompany.com,koppanapavansai@gmail.com
# Alternative: Use Clerk User IDs
SUPER_ADMIN_USER_IDS=user_39exmO6dkqVBZAWkcBX1UaNZ3nL

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,https://yourapp.vercel.app

# Server Configuration
PORT=5000
Frontend Environment Variables
Create UI/.env.local:

bash
# Clerk Configuration
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_publishable_key
CLERK_SECRET_KEY=sk_test_your_clerk_secret_key

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:5000

# Clerk Routes
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/pending
🗄️ Database Setup
1. Create Database
sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database
CREATE DATABASE case_counsil;

-- Connect to database
\c case_counsil
2. Initialize Schema
Option A: Using API endpoint

bash
# Start backend server
python app.py

# Initialize database schema
curl http://localhost:5000/api/init-db
Option B: Manual SQL

sql
-- Schema: legal_saas
CREATE SCHEMA IF NOT EXISTS legal_saas;

-- Table: org_signups
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_org_signups_status
ON legal_saas.org_signups(status);

CREATE INDEX IF NOT EXISTS idx_org_signups_email
ON legal_saas.org_signups(email);

CREATE INDEX IF NOT EXISTS idx_org_signups_created
ON legal_saas.org_signups(created_at DESC);
🚀 Running the Application
Development Mode
Terminal 1 - Backend:

bash
# Activate virtual environment
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate     # Windows

# Run Flask server
python app.py
Backend runs on: http://localhost:5000

Terminal 2 - Frontend:

bash
# Navigate to frontend
cd UI

# Run Next.js dev server
npm run dev
# or
yarn dev
Frontend runs on: http://localhost:3000

Production Mode
Backend:

bash
# Using gunicorn (production WSGI server)
gunicorn -w 4 -b 0.0.0.0:5000 app:app
Frontend:

bash
# Build for production
npm run build

# Start production server
npm start
👥 User Roles & Permissions
Role Hierarchy
text
┌─────────────────────────────────────────────────────────┐
│                    Super Admin                          │
│  - Platform-wide access                                 │
│  - Approve/reject organization signups                  │
│  - Manage all organizations                             │
│  - No organization affiliation                          │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                  Organization Admin                     │
│  - Manage organization settings                         │
│  - Invite/remove organization members                   │
│  - Access all organization data                         │
│  - Role: org:admin in Clerk                             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                 Organization Member                     │
│  - Access own data                                      │
│  - Limited organization access                          │
│  - Role: org:member in Clerk                            │
└─────────────────────────────────────────────────────────┘
Route Access Control
Route	Super Admin	Org Admin	Org Member	Guest
/sign-up	✅	✅	✅	✅
/sign-in	✅	✅	✅	✅
/super-admin	✅	❌	❌	❌
/super-admin/approvals	✅	❌	❌	❌
/admin	❌	✅	❌	❌
/user	❌	❌	✅	❌
/pending	✅	✅	✅	✅
🔌 API Endpoints
Authentication
POST /api/check-user
Verify JWT token and return user role.

Headers:

text
Authorization: Bearer <clerk_jwt_token>
Response:

json
{
  "role": "super-admin" | "org:admin" | "org:member" | null,
  "user_info": {
    "user_id": "user_123",
    "email": "admin@example.com",
    "org_id": "org_456",
    "org_role": "org:admin"
  }
}
Organization Signup
POST /api/register-org
Submit organization signup request.

Request Body:

json
{
  "adminName": "John Doe",
  "organizationName": "Acme Corp",
  "email": "admin@acme.com",
  "password": "securepass123",
  "numberOfSeats": 10
}
Response:

json
{
  "status": "success",
  "message": "Registration submitted successfully",
  "signup_id": 1708123456789
}
Signup Management
GET /api/signups
Fetch all organization signups (all statuses).

Response:

json
{
  "status": "success",
  "count": 5,
  "signups": [
    {
      "id": 1708123456789,
      "admin_name": "John Doe",
      "organization_name": "Acme Corp",
      "email": "admin@acme.com",
      "number_of_seats": 10,
      "status": "pending",
      "created_at": "2026-02-16T10:30:00"
    }
  ]
}
GET /api/signups/pending
Fetch only pending signups.

Response: Same format as /api/signups but filtered by status='pending'

GET /api/signups/<signup_id>
Fetch single signup by ID.

Response:

json
{
  "status": "success",
  "signup": {
    "id": 1708123456789,
    "admin_name": "John Doe",
    "organization_name": "Acme Corp",
    "email": "admin@acme.com",
    "number_of_seats": 10,
    "status": "pending",
    "created_at": "2026-02-16T10:30:00",
    "approved_at": null,
    "rejected_at": null,
    "clerk_org_id": null
  }
}
GET /api/db-stats
Get database statistics.

Response:

json
{
  "status": "success",
  "stats": {
    "total": 10,
    "pending": 3,
    "approved": 6,
    "rejected": 1
  }
}
Approval Management
POST /api/approve-signup
Approve pending organization signup (creates Clerk organization).

Request Body:

json
{
  "signup_id": 1708123456789,
  "admin_user_id": "user_123"
}
Response:

json
{
  "status": "approved",
  "signup_id": 1708123456789,
  "clerk_org_id": "org_456",
  "clerk_org_slug": "acme-corp-123"
}
POST /api/reject-signup
Reject pending organization signup.

Request Body:

json
{
  "signup_id": 1708123456789,
  "rejected_by": "user_123",
  "reason": "Invalid organization details"
}
Response:

json
{
  "status": "rejected",
  "signup_id": 1708123456789,
  "message": "Signup rejected successfully"
}
Utility Endpoints
GET /health
Database health check.

Response:

json
{
  "db_healthy": true
}
GET /api/init-db
Initialize database schema (create tables and indexes).

Response:

json
{
  "status": "success",
  "message": "Database initialized successfully"
}
🚢 Deployment
Backend Deployment (Render)
Create New Web Service on Render

Connect GitHub Repository

Environment Variables:

text
FLASK_ENV=production
DATABASE_URL=<render_postgres_internal_url>
CLERK_SECRET_KEY=<your_clerk_secret>
SUPER_ADMIN_EMAILS=<comma_separated_emails>
ALLOWED_ORIGINS=https://yourapp.vercel.app
SECRET_KEY=<generate_random_secret>
Build Command:

bash
pip install -r requirements.txt
Start Command:

bash
gunicorn -w 4 -b 0.0.0.0:$PORT app:app
Initialize Database:

bash
# After first deployment
curl https://your-backend.onrender.com/api/init-db
Frontend Deployment (Vercel)
Connect GitHub Repository to Vercel

Root Directory: UI

Environment Variables:

text
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=<your_key>
CLERK_SECRET_KEY=<your_secret>
NEXT_PUBLIC_API_URL=<your_backend_url>
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/pending
Build Settings:

Framework Preset: Next.js

Build Command: npm run build

Output Directory: .next

Install Command: npm install

Deploy

Post-Deployment Checklist
 Database initialized (/api/init-db)

 Super admin email configured

 CORS origins updated

 Clerk webhook configured (if needed)

 SSL/HTTPS enabled

 Environment variables verified

 Test signup flow

 Test approval flow

 Monitor logs

📁 Project Structure
text
case-counsil/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── .env                            # Backend environment variables (not in git)
├── .gitignore                      # Git ignore file
├── README.md                       # This file
│
├── auth/                           # Authentication modules
│   ├── __init__.py
│   └── token_verification.py      # JWT verification with Clerk
│
├── utils/                          # Utility functions
│   ├── __init__.py
│   └── logging_errors.py          # Logging utilities
│
├── db_func.py                      # Database operations (all DB functions)
├── clerk_client.py                 # Clerk API client
├── approve_signup_service.py      # Approval workflow logic
├── routing_rules.py               # Role-based routing rules
│
└── UI/                             # Next.js frontend
    ├── app/                        # Next.js App Router
    │   ├── layout.tsx              # Root layout (ClerkProvider)
    │   ├── page.tsx                # Home page (redirects)
    │   │
    │   ├── sign-in/
    │   │   └── [[...sign-in]]/
    │   │       └── page.tsx        # Clerk sign-in page
    │   │
    │   ├── sign-up/
    │   │   └── page.tsx            # Custom sign-up page
    │   │
    │   ├── pending/
    │   │   └── page.tsx            # Pending approval page
    │   │
    │   ├── user/
    │   │   ├── layout.tsx          # User section layout
    │   │   └── page.tsx            # User dashboard
    │   │
    │   ├── admin/
    │   │   └── page.tsx            # Admin dashboard
    │   │
    │   └── super-admin/
    │       ├── page.tsx            # Super admin dashboard (stats)
    │       └── approvals/
    │           └── page.tsx        # Approvals management
    │
    ├── components/                 # Reusable React components
    ├── public/                     # Static assets
    ├── styles/                     # Global styles
    │
    ├── .env.local                  # Frontend environment variables (not in git)
    ├── package.json                # Node.js dependencies
    ├── tsconfig.json               # TypeScript config
    ├── tailwind.config.js          # Tailwind CSS config
    └── next.config.js              # Next.js config
🔒 Security
Implemented Security Measures
1. Authentication
✅ JWT token verification with Clerk's JWKS

✅ Token expiration checks

✅ Secure session management

✅ Authorization header (industry standard)

2. Password Security
✅ bcrypt hashing with automatic salting

✅ Minimum 8 character requirement

✅ No plain text password storage

✅ No passwords in logs

3. API Security
✅ Rate limiting (Flask-Limiter)

5 signups per hour per IP

10 approvals per minute

100 reads per minute

✅ CORS protection with allowed origins

✅ Input validation and sanitization

✅ SQL injection prevention (parameterized queries)

✅ XSS prevention (HTML escaping)

4. Data Protection
✅ HTTPS in production (automatic on Render/Vercel)

✅ Environment variables for secrets

✅ Sensitive data excluded from logs

✅ Database connection encryption

5. Authorization
✅ Role-based access control

✅ Server-side permission checks

✅ Organization data isolation

✅ Super admin identification

Security Best Practices
Environment Variables:

bash
# ❌ Never do this
CLERK_SECRET_KEY="sk_test_abc123"  # Committed to git

# ✅ Always do this
CLERK_SECRET_KEY=sk_test_abc123    # In .env (gitignored)
Password Handling:

python
# ❌ Never do this
write_log(f"User password: {password}")

# ✅ Always do this
write_log(f"User signup: {email}")  # No password
SQL Queries:

python
# ❌ Never do this
cur.execute(f"SELECT * FROM users WHERE email = '{email}'")

# ✅ Always do this
cur.execute("SELECT * FROM users WHERE email = %s", (email,))
Security Checklist
 Use HTTPS in production

 Validate all user inputs

 Sanitize HTML content

 Use parameterized SQL queries

 Hash passwords with bcrypt

 Verify JWT tokens

 Implement rate limiting

 Configure CORS properly

 Use environment variables

 No secrets in code

 No sensitive data in logs

 Regular dependency updates

🐛 Troubleshooting
Common Issues
1. Database Connection Error
Error: Failed to connect to database

Solution:

bash
# Check DATABASE_URL format
# Correct: postgresql://username:password@host:port/database

# Test connection
psql $DATABASE_URL

# Check PostgreSQL is running
sudo service postgresql status  # Linux
brew services list              # Mac

# Initialize database
curl http://localhost:5000/api/init-db
2. Clerk Authentication Error
Error: Invalid token or Token verification failed

Solution:

bash
# 1. Verify Clerk keys
echo $CLERK_SECRET_KEY
# Should start with: sk_test_ or sk_live_

# 2. Check frontend key
cat UI/.env.local | grep CLERK
# Should have: NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...

# 3. Clear browser data
# Chrome: Ctrl+Shift+Delete → Clear cookies and cache

# 4. Sign out and sign in again
3. CORS Error
Error: Access-Control-Allow-Origin error in browser console

Solution:

bash
# 1. Update .env
ALLOWED_ORIGINS=http://localhost:3000,https://yourapp.vercel.app

# 2. Restart Flask
python app.py

# 3. Check browser console for exact origin
# Add that origin to ALLOWED_ORIGINS
4. Super Admin Not Recognized
Error: Super admin routes to /user instead of /super-admin

Logs:

text
[INFO] check_user: Response prepared - role=None
Solution:

bash
# 1. Add email to .env
SUPER_ADMIN_EMAILS=youremail@example.com

# 2. Or add user ID
SUPER_ADMIN_USER_IDS=user_39exmO6dkqVBZAWkcBX1UaNZ3nL

# 3. Restart backend
python app.py

# 4. Sign out and sign in again

# 5. Check logs
# Should see: "User identified as SUPER ADMIN"
5. Port Already in Use
Error: Address already in use on port 5000 or 3000

Solution:

bash
# Kill process on port
# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Mac/Linux:
lsof -ti:5000 | xargs kill -9

# Or use different port
PORT=5001 python app.py
6. Module Not Found Error
Error: ModuleNotFoundError: No module named 'flask'

Solution:

bash
# 1. Activate virtual environment
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Verify installation
pip list | grep Flask
7. Database Table Not Found
Error: relation "legal_saas.org_signups" does not exist

Solution:

bash
# Initialize database schema
curl http://localhost:5000/api/init-db

# Or manually run SQL
psql $DATABASE_URL -f schema.sql
8. Frontend Build Error
Error: Module not found or Cannot find module

Solution:

bash
# 1. Clear node_modules
cd UI
rm -rf node_modules package-lock.json

# 2. Reinstall
npm install

# 3. Clear Next.js cache
rm -rf .next

# 4. Rebuild
npm run build
🧪 Testing
Manual Testing Checklist
Organization Signup Flow
 Navigate to /sign-up

 Fill out form with valid data

 Submit form

 Check: Data saved in database (SELECT * FROM legal_saas.org_signups;)

 Check: Status is 'pending'

 Navigate to /pending

 Verify pending message displayed

Super Admin Approval Flow
 Sign in as super admin

 Navigate to /super-admin

 Verify stats displayed correctly

 Navigate to /super-admin/approvals

 Verify pending signups listed

 Click "Approve" on a signup

 Check: Clerk organization created

 Check: Database status updated to 'approved'

 Check: Signup removed from pending list

Role-Based Routing
 Sign in as super admin → Routes to /super-admin

 Sign in as org admin → Routes to /admin

 Sign in as org member → Routes to /user

 No role → Routes to /pending

API Testing with cURL
bash
# 1. Health check
curl http://localhost:5000/health

# 2. Initialize database
curl http://localhost:5000/api/init-db

# 3. Organization signup
curl -X POST http://localhost:5000/api/register-org \
  -H "Content-Type: application/json" \
  -d '{
    "adminName": "Test Admin",
    "organizationName": "Test Org",
    "email": "test@example.com",
    "password": "password123",
    "numberOfSeats": 5
  }'

# 4. Get pending signups
curl http://localhost:5000/api/signups/pending

# 5. Get database stats
curl http://localhost:5000/api/db-stats

# 6. Approve signup (requires token)
curl -X POST http://localhost:5000/api/approve-signup \
  -H "Content-Type: application/json" \
  -d '{
    "signup_id": 1708123456789,
    "admin_user_id": "user_123"
  }'
🤝 Contributing
Development Workflow
Fork the repository

bash
git clone https://github.com/yourusername/case-counsil.git
Create a feature branch

bash
git checkout -b feature/amazing-feature
Make your changes

Follow code style guidelines

Add tests if applicable

Update documentation

Commit your changes

bash
git commit -m 'feat: add amazing feature'
Push to the branch

bash
git push origin feature/amazing-feature
Open a Pull Request

Describe your changes

Reference related issues

Wait for code review

Code Style
Python (Backend):

Follow PEP 8

Use type hints where possible

Document functions with docstrings

Keep functions focused and small

TypeScript (Frontend):

Use Prettier for formatting

Follow ESLint rules

Use meaningful variable names

Add JSDoc comments for complex functions

Commit Messages:

text
feat: add user authentication
fix: resolve database connection issue
docs: update README with deployment steps
refactor: simplify approval logic
test: add tests for signup endpoint
Testing Requirements
All new features must include tests

Maintain test coverage above 80%

Run tests before submitting PR

📄 License
This project is proprietary and confidential. All rights reserved.

Copyright © 2026 Case Counsil. All rights reserved.

Unauthorized copying, distribution, or modification of this software is strictly prohibited.

📧 Support
Getting Help
Documentation: Read this README thoroughly

Issues: GitHub Issues

Email: support@casecounsil.com

Discord: Join our community

Reporting Bugs
When reporting bugs, please include:

Steps to reproduce

Expected behavior

Actual behavior

Screenshots (if applicable)

Browser/OS information

Error messages and logs

Feature Requests
We welcome feature requests! Please open an issue with:

Clear description of the feature

Use case and benefits

Mockups or examples (if applicable)

🙏 Acknowledgments
This project is built with amazing open-source technologies:

Clerk.dev - Authentication and user management

Flask - Python web framework

Next.js - React framework

PostgreSQL - Database

Tailwind CSS - CSS framework

Render - Backend hosting

Vercel - Frontend deployment

Special thanks to all contributors and the open-source community!

📊 Project Status
Version: 1.0.0

Status: Active Development

Last Updated: February 16, 2026

Maintainers: Case Counsil Team

🗺️ Roadmap
Phase 1 (Current)
 User authentication with Clerk

 Organization signup workflow

 Super admin approval system

 Role-based dashboards

Phase 2 (In Progress)
 Email notifications

 Organization invite system

 User management for org admins

 Activity logs and audit trail

Phase 3 (Planned)
 Case management features

 Document upload and storage

 Advanced search and filtering

 Reporting and analytics

Phase 4 (Future)
 Mobile app

 Third-party integrations

 API for external services

 White-label solution

Built with ❤️ by the Case Counsil Team

For a better legal workflow management experience

Quick Links
Documentation

API Reference

Changelog

Contributing Guidelines

Code of Conduct
```
