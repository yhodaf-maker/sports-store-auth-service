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
