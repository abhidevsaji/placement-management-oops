# Campus Placement Management System

Django + Django REST Framework + MySQL backend, React (Vite) frontend. Built from the four UML diagrams
(use case, class, activity, sequence).

## 1. Backend (build and test this first)
```bash
cd backend
python -m venv venv && source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# MySQL: create the database once
#   mysql -u root -p -e "CREATE DATABASE placement_db CHARACTER SET utf8mb4;"
export DB_ENGINE=mysql DB_NAME=placement_db DB_USER=root DB_PASSWORD=yourpassword   # Windows: set VAR=value
# (no MySQL yet? use  export DB_ENGINE=sqlite  to try everything locally)

python manage.py migrate
python manage.py test                 # 12 tests covering the whole workflow
python manage.py seed_demo            # optional demo users/data (password: Demo@12345)
python manage.py create_admin you@college.edu "Your Name" "StrongPass#123"   # real admin
python manage.py runserver            # API at http://127.0.0.1:8000/api/
```
Demo logins: admin@college.edu, officer@college.edu, student1@college.edu (all `Demo@12345`).
`pending@college.edu` is an unapproved student: log in as admin and approve it.

## 2. Frontend (React)
```bash
cd frontend
npm install
npm run dev                           # http://localhost:5173  (proxies /api to Django)
```

## 3. How the frontend and backend are connected
Django serves a JSON API under `/api/`; React calls it with `fetch` and sends the login token in an
`Authorization` header (`frontend/src/api.js`). Two ways to run them together:

* **Development (two terminals, live reload):** `python manage.py runserver` + `npm run dev`, open http://localhost:5173.
  Vite forwards every `/api` request to Django (`vite.config.js`).
* **One server (like production):** `cd frontend && npm install && npm run build`, then
  `python manage.py runserver` and open http://127.0.0.1:8000 - Django serves the built React app itself (`config/urls.py`).

## Where is the database?
In **MySQL**, on your computer. Django creates the tables when you run `python manage.py migrate`; the connection
settings are in `backend/config/settings.py` (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`). View the tables with
MySQL Workbench or `mysql -u root -p placement_db`, then `SHOW TABLES;`.
`DB_ENGINE=sqlite` switches to a single file `backend/db.sqlite3` for quick testing only.
Uploaded resumes are stored as PDF files in `backend/media/resumes/` (the database stores only the file path).
They are never public: they open only through `/api/students/<id>/resume/` after a permission check.

## New features
* **Account verification (Admin):** *Verify accounts* page with Students / Placement officers tabs. Review opens a
  detail window (roll no, branch, CGPA, phone, resume), then Verify or Reject with a required reason. The reason is
  shown to the user at login, and who verified and when is recorded.
* **Resume:** students drag-and-drop a PDF (max 2 MB, checked on the server), replace or remove it. Applying needs a
  resume. Officers and admin open it from the application / review windows.
* **Admin assigns tasks to Placement Officers:** pick a task (add company, post job, set eligibility, review,
  shortlist, schedule drive, notify students, publish results, or custom), the officer, priority, due date and
  related company. The officer is notified, sees it under *My tasks* with a shortcut to the right page, adds a note and
  marks it started or completed, and the admin is notified. Overdue tasks are highlighted.
* **Interactive UI:** toast messages, confirmation and detail windows, live badge counts and new-notification pop-ups
  (refresh every 20 s), application progress tracker, dashboard bars, profile completeness meter, search and filters.

## UML -> code map
| UML | Code |
|---|---|
| User, Student, PlacementOfficer, Admin (inheritance) | `accounts/models.py` (multi-table inheritance) |
| Company, JobPosting, Application, Result, PlacementDrive, Report | `placement/models.py` |
| Activity diagram: valid login -> account approved? -> role dashboard | `accounts/views.py::LoginView`, `App.jsx` role menus |
| Sequence diagram: registration -> admin verifies -> post job -> apply -> shortlist -> publish result -> report | `placement/tests.py::test_full_flow` |
| Task (added at your request, not in the UML) | `placement/models.py::Task` |
| Use cases (register, explore jobs, apply, add company, view placed students, approve users, generate report) | one page per use case in `frontend/src/pages` |

## OOP in the code
* **Inheritance**: `Student`, `PlacementOfficer`, `Admin` extend `User`; the serializers share `_RegisterBase`; permissions share `RolePermission`.
* **Encapsulation**: rules live in model methods: `Application.apply()`, `Application.update_status()` (allowed transitions), `JobPosting.allows()`, `User.update_profile()` (whitelisted fields).
* **Polymorphism**: `get_dashboard_summary()` and `EDITABLE_FIELDS` are overridden per role; one `/api/dashboard/` call returns role-specific data.

## Security
Hashed passwords with Django's validators, token authentication, accounts blocked until admin approval,
role checks on every endpoint (`accounts/permissions.py`), server-side validation (CGPA 0-10, 10-digit phone,
unique email/roll no., no past deadlines, no duplicate applications, valid status transitions).

## Notes
* The Company is a record managed by the Placement Officer (as in your brief); it has no login.
* Notifications are in-app. For email, set Django `EMAIL_BACKEND` and send from `Notification.send`.
* For production set `DJANGO_DEBUG=0`, a real `DJANGO_SECRET_KEY`, and restrict `CORS_ALLOWED_ORIGINS`.
