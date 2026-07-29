# Sports Store Auth Service

FastAPI service responsible for user registration, login, JWT issuance, password hashing, and customer/admin roles.

## Runtime

- Port: `8001`
- Database: `auth_db`
- Health endpoint: `/health`

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8001
```

## Tests

```bash
pytest tests/ -v
```

## PR Diff Review Runner

The offline, provider-independent review pipeline is documented in [`review_runner/README.md`](review_runner/README.md). It accepts a supplied unified PR patch and does not make external API calls.
