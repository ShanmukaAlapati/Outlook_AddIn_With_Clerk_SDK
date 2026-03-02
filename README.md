# Case Counsel — Outlook Add-in

## Quick Start

### 1. Frontend (Next.js)
```bash
cd frontend
npm install
# Edit .env.local — paste your CLERK_SECRET_KEY
npm run dev
```

### 2. Python API
```bash
cd python-api
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
# Edit .env — paste your CLERK_SECRET_KEY
python app.py
```

### 3. Clerk Dashboard
- Allowed redirect URLs: http://localhost:3000/auth-callback
- Home URL: http://localhost:3000

### 4. Load in Outlook
- Outlook → File → Manage Add-ins → Add from file → select manifest.xml

## Folder Structure
```
case-counsel/
├── frontend/
│   ├── pages/
│   │   ├── _app.tsx          # ClerkProvider
│   │   ├── index.tsx         # redirects to /taskpane
│   │   ├── taskpane.tsx      # main add-in UI
│   │   ├── auth-callback.tsx # post sign-in handler
│   │   └── sign-in/
│   │       └── [[...index]].tsx
│   ├── middleware.ts
│   ├── next.config.js
│   └── .env.local
├── python-api/
│   ├── app.py
│   ├── requirements.txt
│   └── .env
└── manifest.xml
```

## Why Pages Router (not App Router)?
Office.js overrides window.history with a stub object.
Next.js App Router calls window.history.replaceState() on every render — this crashes.
Pages Router does not have this dependency, so it works with Office.js.
