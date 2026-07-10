# Sports Attendance System

Django + Bootstrap web app for Christ University Sports Department attendance, scheduling, role management, feedback, and reports.

## Features

- Google-only login through django-allauth.
- Roles: Super Admin, Sub Admin, Captain, Vice Captain, Coordinator, Member.
- Sports, teams, team members, and captain/vice captain/coordinator assignment.
- Practice scheduling with attendance delegation audit trail.
- Attendance statuses: Present, Absent, Late, Early Exit.
- Duplicate attendance prevention per session/member.
- Admin attendance edits with audit history.
- Private feedback between admins/coordinators/students.
- Attendance reports filtered by sport, team, student, and date range.
- Excel and PDF export.

## Run Locally

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Google Login Setup

Create a Google OAuth web client in Google Cloud Console and add this redirect URI:

```text
http://127.0.0.1:8000/accounts/google/login/callback/
```

Download the Google OAuth file and place/update it as:

```text
client_secret.json
```

It should contain:

```json
{
  "web": {
    "client_id": "...",
    "project_id": "...",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "...",
    "redirect_uris": [
      "http://127.0.0.1:8000/accounts/google/login/callback/"
    ]
  }
}
```

Then import it into Django Admin's Social Applications table:

```powershell
.\.venv\Scripts\python.exe manage.py import_google_oauth
```

Or add it manually:

```text
Admin -> Social Accounts -> Social applications -> Add social application
Provider: Google
Name: Google
Client id: value from client_secret.json
Secret key: value from client_secret.json
Sites: 127.0.0.1:8000
```

The first Google user who signs in is automatically promoted to Super Admin for initial setup.
