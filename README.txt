# FinGuard AI — Full-Stack Connected Prototype

## What changed
This version connects the website to a real local FastAPI backend and SQLite database.

### Working modules
- Dashboard data comes from SQLite through API endpoints.
- Transactions are stored in SQLite.
- CSV import writes rows into the database.
- Explainable risk engine calculates a risk score and gives reasons.
- Every medium/high risk includes a practical action/solution plan.
- Clicking transactions opens full details.
- Risk Center shows reason + recommended response.
- AI Analysis pulls live backend metrics.
- Cash-flow forecast comes from backend data.
- AI Assistant sends questions to the backend and uses dashboard data.
- Goals are stored in SQLite.
- Reports are generated from the database.
- Settings are interactive UI toggles.

## Run on Windows
1. Install Python 3.10+.
2. Extract this ZIP.
3. Double-click `run.bat`.
4. Wait for "Uvicorn running..." / "Starting FinGuard AI..."
5. Open: http://127.0.0.1:8000
6. Keep the black terminal window open while using the site.

If Windows blocks `py`, use:
`python -m venv venv`
and replace `py` with `python` in `run.bat`.

## Demo CSV format
date,merchant,category,amount
2026-09-25,Example Store,Shopping,2500
2026-09-24,Example Cafe,Food,700

## Important production note
The backend risk engine here is an explainable prototype, not a bank-grade fraud detector. For a real deployment, connect authenticated bank/financial data, a trained anomaly/fraud model, secure secrets, HTTPS, proper user accounts, PostgreSQL, audit logging and a production LLM/ML service.


## Deploy to Render
This project is prepared as a single Python web service:
- Runtime: Python
- Build Command: pip install -r requirements.txt
- Start Command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
- Root Directory: leave blank
The frontend uses /api, so it works on the same public domain as the FastAPI backend.
