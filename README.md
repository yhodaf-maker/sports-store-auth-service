# Sports Store Auth Service

Authentication service for the Sports Store platform. It registers users, verifies passwords, issues JSON Web Tokens (JWTs), and returns the signed-in user's profile.

## Contents

- [Role in the system](#role-in-the-system)
- [Technology and structure](#technology-and-structure)
- [Configuration](#configuration)
- [Run locally](#run-locally)
- [API](#api)
- [Quality checks](#quality-checks)
- [Docker and deployment](#docker-and-deployment)
- [Security and troubleshooting](#security-and-troubleshooting)

## Role in the system

The browser sends `/api/auth/*` requests to the [gateway](https://github.com/Deploy-On-Friday2-0/sports-store-gateway), which forwards them here on port `8001`. This service stores users in the `auth_db` MongoDB database. It signs JWTs that the catalog, cart, order, and payment services also verify. Redis is used as a cache when configured.

## Technology and structure

- Python, FastAPI, Uvicorn, Pydantic, Motor (asynchronous MongoDB), PyJWT, bcrypt, Redis, and Prometheus instrumentation.
- `main.py` creates the application, metrics, startup checks, and health endpoint.
- `routes/auth.py` implements the authentication API.
- `models.py`, `database.py`, `security.py`, and `cache.py` contain data, persistence, token/password, and caching logic.
- `tests/` contains pytest tests; `.github/workflows/` contains CI and image-publishing automation.
- `review_runner/` is the optional AI pull-request reviewer; see [its README](review_runner/README.md).

## Configuration

Copy `.env.example` to `.env`. FastAPI loads that file at startup.

| Variable | Purpose | Example/default |
| --- | --- | --- |
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `JWT_SECRET` | Shared token-signing secret | Required outside disposable local use |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime | `60` |
| `REDIS_HOST`, `REDIS_PORT` | Standalone Redis connection | `localhost`, `6379` |
| `REDIS_SENTINELS`, `REDIS_MASTER_NAME` | Optional Sentinel connection | unset, `mymaster` |
| `REDIS_PASSWORD`, `REDIS_SOCKET_TIMEOUT` | Optional Redis authentication and timeout | unset, `0.2` seconds |

The `OPENROUTER_*` entries in `.env.example` apply only to the optional review runner, not the application. Never commit real credentials.

## Run locally

Prerequisites: Python 3, MongoDB, and optionally Redis. The easiest full-system setup is [sports-store-local](https://github.com/Deploy-On-Friday2-0/sports-store-local).

```bash
python -m venv .venv
source .venv/bin/activate       # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env           # PowerShell: Copy-Item .env.example .env
uvicorn main:app --reload --port 8001
```

Open `http://localhost:8001/docs` for interactive OpenAPI documentation.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/auth/register` | Create a user |
| `POST` | `/api/auth/login` | Return a bearer token |
| `GET` | `/api/auth/me` | Return the authenticated user |
| `GET` | `/health` | Report MongoDB and Redis readiness |
| `GET` | `/metrics` | Prometheus metrics |

## Quality checks

```bash
ruff check .
pytest
python -m pip check
docker build -t sports-store-auth-service:local .
```

CI workflow `PR Quality and Security` validates branch names, runs Ruff and pytest, checks dependencies, scans secrets with Gitleaks, checks the Dockerfile with Checkov, and scans the built image with Trivy. `Publish Production Image` builds and pushes a versioned image to Amazon ECR, then updates the image value in the deployments repository.

## Docker and deployment

```bash
docker build -t sports-store-auth-service:local .
docker run --rm -p 8001:8001 --env-file .env sports-store-auth-service:local
```

Production Kubernetes configuration belongs to [sports-store-deployments](https://github.com/Deploy-On-Friday2-0/sports-store-deployments); AWS resources and ECR belong to [sports-store-infrastructure](https://github.com/Deploy-On-Friday2-0/sports-store-infrastructure).

## Security and troubleshooting

- Use the same strong `JWT_SECRET` in every backend service, and store production secrets in a secret manager.
- A MongoDB health failure usually means `MONGO_URI` is wrong or MongoDB is not ready. A Redis failure is reported by `/health`; verify the standalone or Sentinel variables.
- `401 Unauthorized` usually means the bearer token is missing, expired, or signed with a different secret.
- Follow [CONTRIBUTING.md](CONTRIBUTING.md) for the branch and pull-request workflow.
