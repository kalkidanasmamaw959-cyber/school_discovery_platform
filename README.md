# EduConnect Ethiopia

EduConnect Ethiopia is a school discovery platform for Addis Ababa, Bahir Dar,
Hawassa and Adama. Families can browse and compare schools, read posts, submit
reviews and get transparent, explainable school recommendations. Schools can
register, manage their own profile and posts, and submit Ministry of Education
certification information for administrator review.

This project uses the existing UI and SQLite database. The database is upgraded
in place at startup; no existing tables or seeded rows are deleted.

## Features

- School discovery from the real SQLite database (no hard-coded school cards).
- City, education level, name/location and verification filters.
- School profile pages with programs, facilities, contact links, posts and
  family reviews.
- Public review submission with validation and administrator moderation.
- School registration, login, logout, secure password hashing and token
  sessions.
- School dashboard: edit own profile, manage own posts, view own reviews, submit
  certification, and see verification history.
- Administrator console: review certification submissions, approve or reject
  schools, manage users, hide/delete reviews and posts.
- Explainable recommendation algorithm with per-school reasons, missing-data
  notes and side-by-side comparison.
- Optional external AI summary only when explicitly configured; the core
  recommendation feature never requires a paid service.
- Safe automatic schema migration for the existing SQLite database.

## Technology

- Backend: Flask, Flask-SQLAlchemy, Flask-CORS, SQLite
- Auth: Werkzeug password hashing, random bearer tokens stored as SHA-256 hashes
- Frontend: existing HTML/CSS/JavaScript (no framework)
- Tests: pytest with an isolated temporary database

## Project structure

```text
.
├── index.html                 # discovery, school details, recommendations
├── school-register.html       # school registration + certification fields
├── school-login.html          # school/admin sign-in
├── dashboard.html             # protected school dashboard
├── admin.html                 # protected administrator console
├── style.css                  # existing design + new component styles
├── api-config.js              # one shared API base for Flask/Live Server
├── script.js                  # database-backed public discovery + reviews
├── registration.js            # registration API integration
├── login.js                   # login API integration
├── dashboard.js               # school dashboard API integration
├── admin.js                   # administrator API integration
├── backend/
│   ├── app.py                 # app factory, routes, validation, migrations
│   ├── models.py              # SQLAlchemy models
│   ├── seed.py                # idempotent original-school seeding
│   ├── create_admin.py        # secure admin creation/promotion/password reset
│   └── requirements.txt
├── instance/
│   └── educonnect.db          # existing SQLite database (migrated in place)
├── tests/
│   └── test_api.py
├── .env.example
├── .gitignore
└── README.md
```

## Requirements

- Windows 10 or newer.
- Python 3.10 or newer with `pip` (tested here with Python 3.14).
- A modern browser (Chrome, Edge or Firefox).
- Optional: Node.js only for the JavaScript syntax checks.
- Optional: VS Code with Live Server, or use Flask to serve the frontend.

No Node.js server, database server or cloud account is required. SQLite is
included with Python.

## Quick setup on Windows

Open PowerShell **inside the project folder** (the folder containing
`index.html`). In File Explorer, right-click the folder and choose
**Open in Terminal**, or use:

```powershell
Set-Location "C:\path\to\your\project-folder"
```

Do not copy a `.venv` folder from another computer. Create a fresh one:

```powershell
# 1. Check Python
python --version

# 2. Create an isolated environment
python -m venv .venv

# 3. Install the required packages
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# 4. Verify the existing database and school records
.\.venv\Scripts\python.exe -m backend.seed --check
```

If `python` is not recognized, install Python from
<https://www.python.org/downloads/windows/> and enable **Add python.exe to
PATH** during installation.

Using `.\.venv\Scripts\python.exe` avoids PowerShell activation-policy
problems. If you prefer activation, run `.\.venv\Scripts\Activate.ps1` and then
use `python` normally.

### Optional local configuration

The app runs without a `.env` file. For a stable secret key, create one:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and replace `SECRET_KEY` with a generated value. Never commit
`.env`; it is already ignored.

### Create an administrator

The project does **not** include a default admin password. If the database has
no admin account, create one locally. The password prompt is hidden and the
password is not stored in the repository:

```powershell
.\.venv\Scripts\python.exe -m backend.create_admin --username admin --email YOU@example.com
```

Promote an existing account or reset its password:

```powershell
.\.venv\Scripts\python.exe -m backend.create_admin --username admin --promote
.\.venv\Scripts\python.exe -m backend.create_admin --username admin --reset-password
```

The administrator signs in through the normal login page and is redirected to
the admin console.

## Run the application

### Recommended: Flask serves both API and frontend

```powershell
.\.venv\Scripts\python.exe -m backend.app
```

Open:

- App: <http://127.0.0.1:5000/app/>
- Login: <http://127.0.0.1:5000/app/school-login.html>
- API health: <http://127.0.0.1:5000/api/health>

The backend uses port **5000** by default. If port 5000 is unavailable, start
Flask on 5001 with `$env:FLASK_PORT=5001`; `api-config.js` checks both ports
automatically when the frontend is served by Live Server.

### Optional: VS Code Live Server

Keep Flask running, then serve the frontend on a permitted port such as 5501:

```powershell
.\.venv\Scripts\python.exe -m http.server 5501 --bind 127.0.0.1
```

Open the URL shown by Live Server. The default CORS configuration allows
Live Server ports `5500` through `5505`.

`api-config.js` selects the API automatically:

- Served by Flask under `/app/` → same origin.
- Served from Live Server → checks `http://127.0.0.1:5000` first, then
  `http://127.0.0.1:5001`.
- `window.EDUCONNECT_API_BASE` can override the API URL before `api-config.js`
  is loaded.

**Do not open the HTML files with `file://`.** Use Flask or a local HTTP server.

Use `127.0.0.1` rather than `localhost` if another local program occupies the
same port on IPv6. Test the backend directly at
<http://127.0.0.1:5000/api/health>.

## Moving the project to another PC

Copy the whole project folder, including:

- `instance\educonnect.db` — your existing database and school records.
- `instance\backups\` — optional database backups.
- All source files, especially the updated `.js` files, `.env.example`,
  `backend\requirements.txt` and `tests\`.

Do **not** copy `.venv`, `__pycache__`, or `.pytest_cache`. Recreate `.venv` on
the new PC with the setup commands above.

The application locates the database relative to `backend\app.py`, not relative
to the current PowerShell folder. A relative `DATABASE_PATH` such as
`instance/educonnect.db` is resolved from the project root.

## Environment configuration

Copy `.env.example` to `.env`. Supported variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | random per startup | Flask secret; set a stable random value |
| `DATABASE_PATH` | `instance/educonnect.db` | SQLite file; relative paths resolve from project root |
| `DATABASE_URL` | derived from `DATABASE_PATH` | Full SQLAlchemy database URL override |
| `CORS_ORIGINS` | local ports 5000/5001/5500–5505/8000/8080 | Comma-separated allowed browser origins |
| `FLASK_HOST` | `127.0.0.1` | Backend bind address |
| `FLASK_PORT` | `5000` | Backend port |
| `FLASK_DEBUG` | `0` | Set to `1` only for local development |
| `ADMIN_PASSWORD` | unset | Optional non-interactive admin password for CLI |
| `EDUCONNECT_ENABLE_AI` | `0` | Enable optional external AI summary |
| `OPENAI_API_KEY` | unset | External AI key; never commit it |
| `OPENAI_MODEL` | unset | Model name for the external AI summary |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible API base URL |

If `OPENAI_API_KEY` and `OPENAI_MODEL` are not both set, recommendations use the
local explainable algorithm and the response explicitly says no external AI was
called.

## Database and migrations

The app calls `db.create_all()` and then `ensure_schema()` at startup.
`ensure_schema()` uses SQLite `PRAGMA table_info` and `ALTER TABLE ... ADD COLUMN`
to add new fields safely. It also creates missing indexes and new tables:

- `school`: programs, facilities, certification fields, verification metadata,
  timestamps.
- `user`: active flag, timestamps.
- `post`: hidden flag, updated timestamp, author.
- `review`: hidden/moderation metadata.
- `verification_record`: certification submissions and review decisions.
- `auth_token`: hashed bearer sessions with expiry.

Before a major upgrade, make a local backup:

```powershell
Copy-Item instance\educonnect.db instance\educonnect.backup.db
```

Do not reset or delete the database to fix migration issues. If a migration
fails, keep the database and share the error details.

## Authentication and authorization

- Passwords are hashed with Werkzeug; hashes are never returned by the API.
- Login returns a random bearer token. Only a SHA-256 hash is stored in SQLite.
- Tokens expire after 7 days (30 days when "Remember me" is selected), can be
  revoked by logout, and are revoked when an account is disabled.
- Public endpoints need no login. School profile/post management requires a
  school token and ownership of that school. Admin endpoints require the
  `admin` role.
- Users cannot edit another school's profile or manage another school's posts.
- Deactivating or resetting a user revokes their tokens.
- CORS is restricted to configured local origins.

## API reference

Public:

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/health` | Health and database connectivity |
| GET | `/api/meta` | Cities, levels, known facilities/programs, fee-data note |
| GET | `/api/schools?city=&level=&search=&verified=` | List/search/filter schools |
| GET | `/api/schools/<id>` | School details, public posts and reviews |
| GET | `/api/schools/<id>/posts` | Public posts for a school |
| POST | `/api/schools/<id>/reviews` | Submit a review |
| POST | `/api/recommendations` | Explainable recommendations |

Authentication:

| Method | Endpoint | Auth |
| --- | --- | --- |
| POST | `/api/auth/register` | Public |
| POST | `/api/auth/login` | Public |
| POST | `/api/auth/logout` | Bearer token |
| GET | `/api/auth/me` | Bearer token |

School account:

| Method | Endpoint | Description |
| --- | --- | --- |
| GET, PUT | `/api/school/me` | Read/update own school profile |
| POST | `/api/school/verification` | Submit/resubmit certification |
| GET | `/api/school/posts` | Own posts (including hidden) |
| GET | `/api/school/reviews` | Own reviews (including hidden) |
| POST | `/api/schools/<id>/posts` | Create a post for own school |
| PUT, DELETE | `/api/posts/<id>` | Update/delete own post |

Administrator (requires `admin` role):

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/admin/stats` | Platform counts |
| GET | `/api/admin/schools?status=` | List schools by verification status |
| GET | `/api/admin/schools/<id>` | Full school/certification/account detail |
| POST | `/api/admin/schools/<id>/verify` | Approve and verify a school |
| POST | `/api/admin/schools/<id>/reject` | Reject a school (reason required) |
| GET | `/api/admin/users` | List users |
| PATCH, DELETE | `/api/admin/users/<id>` | Enable/disable or delete a user |
| GET | `/api/admin/posts` | List all posts |
| PATCH | `/api/admin/posts/<id>` | Hide/restore a post |
| GET | `/api/admin/reviews` | List all reviews |
| PATCH, DELETE | `/api/admin/reviews/<id>` | Hide/restore or delete a review |

### Example registration body

```json
{
  "school_name": "Example Academy",
  "city": "Adama",
  "level": "Primary & Secondary",
  "location": "Adama, Ethiopia",
  "school_email": "info@example.school",
  "phone": "+251911222333",
  "website": "https://example.school",
  "username": "exampleacademy",
  "password": "a-long-unique-password",
  "confirm_password": "a-long-unique-password",
  "certification_number": "MOE-EXAMPLE-123",
  "certification_issuer": "Ministry of Education",
  "certification_url": "https://example.school/certificate"
}
```

### Example recommendation body

```json
{
  "city": "Bahir Dar",
  "level": "Primary",
  "facilities": ["Library", "Computer Lab"],
  "programs": ["Primary", "Secondary"],
  "verified_only": false,
  "limit": 6
}
```

## Recommendation behavior

The default engine is transparent and rule-based. Weights:

| Factor | Weight |
| --- | --- |
| City match | 30 |
| Education level match | 20 |
| Preferred facilities | 20 |
| Preferred programs | 10 |
| Admin verification | 10 |
| Contact information completeness | 5 |
| Published family reviews | 5 |

Only applicable factors are included in the maximum score, which is normalized
to 100. Each school receives:

- a match score and raw score,
- per-factor explanations with matched/partial/missing/unmatched status,
- a `missing_information` list,
- a verification status and label.

Important honesty rules:

- Fees are **not** collected, so cost/budget is not scored and no fees are
  invented.
- Facilities, programs, ratings, accreditation and quality are never guessed.
  Missing data reduces a score and is shown to the user.
- A pending school is clearly labelled unverified.
- Administrator approval means the submitted certification was reviewed by an
  EduConnect administrator; it is not a claim of school quality.

### Optional external AI

The core recommendation always works offline. If you enable and configure an
OpenAI-compatible service, the app may add a short explanatory summary:

```powershell
$env:EDUCONNECT_ENABLE_AI = "1"
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_MODEL = "your-model-name"
```

The API response sets `ai.generated_by_ai` to `true` only after a successful
external response. On any failure it falls back to the rule-based explanations
and clearly states that external AI was unavailable. Never commit API keys.

## School verification

Registration creates a `verification_record` with the submitted Ministry of
Education registration number, issuer and optional reference link. The school
stays `pending` until an administrator reviews it in `admin.html` and explicitly
approves or rejects it.

There is no automatic Ministry of Education registry integration because no
official public API/credentials were provided. The administrator must manually
check the submitted reference before approving. A rejected school is hidden from
public discovery; the school can sign in and resubmit certification.

## Tests

Run the API test suite from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The tests use a temporary SQLite database and do not modify
`instance/educonnect.db`. They cover:

- health and school listing/filter/search,
- legacy database migration with row preservation,
- registration validation, duplicate prevention and password hashing,
- login/logout/token revocation and role checks,
- school ownership authorization,
- profile updates, posts, reviews and rating validation,
- admin approval/rejection, user management and content moderation,
- recommendation explanations, verified-only filtering and missing-data notes,
- CORS preflight.

Optional JavaScript syntax check (if Node.js is installed):

```powershell
node --check script.js
node --check dashboard.js
node --check admin.js
node --check login.js
node --check registration.js
node --check api-config.js
```

Node.js is not needed to run the application.

## Known limitations / external input needed

- **Ministry of Education integration:** no official registry API or credentials
  were supplied. Verification is an administrator-reviewed workflow.
- **External AI:** disabled by default and requires your own key/model if wanted.
  The rule-based recommender is complete without it.
- **Fee data:** not available, so it is deliberately excluded. Do not expect fee
  comparisons until a reliable data source is added.
- **School photos:** dashboard photo previews are local to the browser and are not
  uploaded or persisted. The rest of the profile is persisted in SQLite.
- **Email delivery / automated password reset:** not configured. An administrator
  can reset passwords with
  `.\.venv\Scripts\python.exe -m backend.create_admin --username ... --reset-password`.
- **Seeded school details:** the original seed contains only names, cities and
  some locations. Missing programs, facilities, contact details and descriptions
  are intentionally shown as "not provided" rather than invented. Schools can
  complete their own profiles after registering.

## Troubleshooting

- **"Could not reach the backend"**: start
  `.\.venv\Scripts\python.exe -m backend.app` and open
  `http://127.0.0.1:5000/app/` or the exact URL shown by Live Server.
- **Port 5000 is already in use**: check it with
  `Get-NetTCPConnection -LocalPort 5000 -State Listen`. Stop the other program,
  or start Flask with `$env:FLASK_PORT=5001`; Live Server mode checks both ports.
- **Sign-in reports 404**: verify `http://127.0.0.1:5000/api/health` returns the
  EduConnect JSON. If another program owns the port, stop it, use 5001, or set
  `window.EDUCONNECT_API_BASE` before `api-config.js` loads.
- **Sign In reloads the page and nothing happens**: hard-refresh with
  `Ctrl+F5` and confirm `login.js` was copied. Open the app through
  `http://127.0.0.1:5000/app/school-login.html`; if the page reports that
  `login.js` did not load, recopy the frontend files and restart the browser.
- **On another PC**: copy `instance\educonnect.db` or create an admin there.
  Use `127.0.0.1`, not `localhost`, and open
  `http://127.0.0.1:5000/app/`.
- **CORS error**: add your frontend origin to `CORS_ORIGINS` in `.env` and restart
  Flask. The defaults include Live Server ports 5500 through 5505.
- **No schools**: run `.\.venv\Scripts\python.exe -m backend.seed` and then
  `.\.venv\Scripts\python.exe -m backend.seed --check`.
- **Admin login keeps returning to the login page**: confirm an active admin
  exists in the same database Flask is using. Creating an admin in a different
  database or while using a different origin does not carry over. Create one with
  `.\.venv\Scripts\python.exe -m backend.create_admin --username admin --email you@example.com`,
  then sign in through the same host and port as the admin console.
- **Admin login redirects to dashboard**: the account does not have the `admin`
  role. Use
  `.\.venv\Scripts\python.exe -m backend.create_admin --username <user> --promote`.
- **Database changes not visible**: stop Flask, back up the DB, restart so
  `ensure_schema()` can run, and check the startup log for the database path.
