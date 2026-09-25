# Online Feedback Management System (MVP)

A Flask + Bootstrap web app where users submit feedback and admins review it
on a filterable dashboard. Built to match the mini-project tech stack:
Python Flask, HTML/CSS/Bootstrap, SQLite, Docker, GitHub Actions,
Google Artifact Registry, Cloud Run, Cloud Monitoring/Logging, pytest.

## Features
- **Feedback form**: Name, Register No., Department, Category, Rating (1-5), Comments
- **Admin login**: session-based, hardcoded/env-configurable credentials
- **Admin dashboard**: view all feedback, filter by department/category/rating/status,
  average rating, pending/resolved counts, recent feedback, mark resolved/pending
- **Health endpoint**: `GET /health` -> `{"status": "healthy", ...}` for uptime checks

## Project structure
```
feedback_system/
├── app.py              # Flask app, models, routes
├── templates/           # Jinja2 + Bootstrap templates
├── static/               # (empty - Bootstrap loaded via CDN)
├── requirements.txt
├── Dockerfile
├── test_app.py           # pytest suite (8 tests)
└── README.md
```

## Run locally
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 app.py
# open http://127.0.0.1:8080/feedback
```
Default admin login: `admin` / `admin123`
(override with `ADMIN_USERNAME` / `ADMIN_PASSWORD` env vars).

## Run tests
```bash
pytest test_app.py -v
```

## Docker
```bash
docker build -t feedback-system .
docker run -p 8080:8080 feedback-system
```

## Deploy to Google Cloud Run (outline)
```bash
# 1. Build & push to Artifact Registry
gcloud artifacts repositories create feedback-repo --repository-format=docker --location=us-central1
docker build -t us-central1-docker.pkg.dev/PROJECT_ID/feedback-repo/feedback-system .
docker push us-central1-docker.pkg.dev/PROJECT_ID/feedback-repo/feedback-system

# 2. Deploy
gcloud run deploy feedback-system \
  --image us-central1-docker.pkg.dev/PROJECT_ID/feedback-repo/feedback-system \
  --platform managed --region us-central1 --allow-unauthenticated \
  --set-env-vars ADMIN_USERNAME=admin,ADMIN_PASSWORD=change-me,SECRET_KEY=change-me
```
A minimal `github-actions` workflow can run `pytest`, then build/push the
image and call `gcloud run deploy` on every push to `main` for CI/CD.
Use Cloud Monitoring uptime checks against `/health` and Cloud Logging for
request/error logs to cover the SRE/monitoring requirement.

## Notes for the report
- **SRE practice 1**: `/health` endpoint + Cloud Monitoring uptime check
- **SRE practice 2**: Cloud Logging error/log monitoring on Cloud Run
- **Failure/recovery demo idea**: stop the Cloud Run service or break the DB
  path, show the uptime check failing, fix it, redeploy, show recovery.
