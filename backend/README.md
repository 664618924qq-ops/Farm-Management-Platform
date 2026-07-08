# Livestock Monitoring Backend

## Local setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\activate
pip install -e .[dev]
python scripts/init_mysql.py
```

## Run

```powershell
uvicorn app.main:app --app-dir backend --reload
```

## TCP receiver

```powershell
python backend/app/tcp/server.py
```

## Default MySQL connection

- Host: `127.0.0.1`
- Port: `3306`
- User: `root`
- Password: `zeei`
- Database: `livestock_monitor`
