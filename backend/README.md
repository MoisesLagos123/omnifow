# Mini ERP — Backend (módulo Autenticación)

Solo el flujo de **Login** está implementado en este punto. Refresh / logout / change-password están pendientes (ver `PROGRESO.md`).

## Setup

```bash
cd backend

# 1) venv
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# o bash:
source .venv/Scripts/activate

# 2) instalar deps
pip install -U pip
pip install -e ".[dev]"

# 3) copiar .env y ajustar si hace falta
cp .env.example .env

# 4) generar par de claves JWT (RSA 3072, RS256)
python scripts/generate_jwt_keys.py

# 5) aplicar migraciones (Postgres en Docker)
alembic upgrade head

# 6) crear usuario seed (admin@minierp.cl / Admin12345!)
python scripts/seed_dev_user.py
```

## Levantar la app

```bash
uvicorn erp.main:app --reload --port 8000
```

Docs: http://localhost:8000/docs

## Probar login

```bash
curl -i -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@minierp.cl","password":"Admin12345!"}'
```

## Tests / typecheck / lint

```bash
pytest -q
mypy --strict src/
ruff check src tests
```
