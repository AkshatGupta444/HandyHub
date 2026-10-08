# HandyHub

A full-stack local-services marketplace built with Python, Flask, REST APIs, SQLite, HTML, CSS and JavaScript.

## Features
- Customer and service-provider registration/login
- Password hashing
- Service/provider search
- REST API endpoints
- Service request creation
- Customer/provider dashboards
- Request status updates
- SQLite persistence
- Responsive frontend
- Health endpoint for deployment checks

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

Demo provider accounts are seeded automatically:
- rahul@handyhub.demo / demo123
- amit@handyhub.demo / demo123
- neeraj@handyhub.demo / demo123

Create your own customer account from Register.

## API examples

GET /api/services
GET /api/providers?q=electrician&city=Kanpur
POST /api/register
POST /api/login
GET /api/requests
POST /api/requests
PATCH /api/requests/<id>
DELETE /api/requests/<id>

Authentication uses Flask session cookies.

## Deployment

This project includes Procfile and runtime.txt for platforms that support Gunicorn/Procfile deployment.

Set:
SECRET_KEY = a strong random value

Start command:
gunicorn app:app

Important: SQLite is suitable for a college/demo deployment. For a serious production deployment, move the database to PostgreSQL and add stronger production security, CSRF protection, rate limiting, logging, and proper secret management.
