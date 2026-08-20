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

## Email Notification Setup

Email notifications are disabled until SMTP credentials are supplied through the process environment. For the sender mailbox, configure:

```text
EMAIL_NOTIFICATIONS_ENABLED=true
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_HOST_USER=sports.lavasa@christuniversity.in
EMAIL_HOST_PASSWORD=<mailbox password or app password>
DEFAULT_FROM_EMAIL=sports.lavasa@christuniversity.in
```

For local development, copy `.env.example` to `.env`, set the values there, and restart Django. The project loads the root `.env` file automatically. Operating-system or hosting environment variables take priority over values in `.env`.

Add the app password only to this line in the untracked root `.env` file:

```text
EMAIL_HOST_PASSWORD=your-app-password
```

Do not add it to `.env.example`, `settings.py`, source control, screenshots, or application logs. `.env` is included in `.gitignore`.

The application always uses Gmail SMTP for enabled email notifications. The configured Google account must have 2-Step Verification and a valid app password, and must be allowed to send as `DEFAULT_FROM_EMAIL`.

Test SMTP connectivity and authentication without sending a message:

```powershell
.\.venv\Scripts\python.exe manage.py test_smtp
```

The command reports whether connection/TLS or SMTP-provider authentication failed and never displays the configured password.

## Background Email Worker

Notification emails are queued in the database so web requests never wait for SMTP. During local development, `runserver` automatically starts exactly one background email worker (including when Django's autoreloader is enabled), so this is the only command required:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

The automatic worker stops with the development server. In production, run `run_email_worker` as a continuously supervised service because production WSGI/ASGI servers manage multiple processes differently. It safely retries failed recipients and logs SMTP failures. To process currently queued jobs and exit, use `run_email_worker --once`.
