# Wind Forecast Decision Support (Day-Ahead, UK, Jan 2026)

Live app: <FRONTEND_URL> · API: <BACKEND_URL>/docs

## What it does
For a UK utility buying day-ahead power: shows the latest wind forecast (Elexon WINDFOR) available at
decision time (D-1, 09:00 UK by default), compares it to actual wind (FUELHH), and quantifies the error
(MAE, RMSE, bias, wMAPE, P90) with a procurement what-if that applies a P90 safety buffer.

## AI usage
Built with AI assistance (Claude) for scaffolding, code and documentation; I reviewed and understood all code.

## Structure
- `backend/app/` – FastAPI app: `data.py` (loading), `analysis.py` (domain logic), `main.py` (endpoints)
- `backend/scripts/fetch_data.py` – downloads Jan-2026 data from Elexon into `backend/data/`
- `backend/tests/` – pytest tests; `backend/api/index.py` – Vercel entry point
- `frontend/src/` – React + Recharts dashboard
- `docker-compose.yml` – runs both services

## Run locally
(First run `python scripts/fetch_data.py` once: it downloads Elexon data into `backend/data/`. Commit the two generated `.csv.gz` files so the Vercel deploy has them.)

    cd backend && python -m venv .venv && source .venv/bin/activate
    pip install -r requirements-dev.txt && python scripts/fetch_data.py && pytest -q
    uvicorn app.main:app --reload
    cd frontend && npm install && npm run dev

## Docker
    docker compose up --build   # UI :3000, API :8000

## Key assumptions
- Decision time = D-1 at 09:00 UK (configurable in UI); UK = UTC in January.
- Error = forecast − actual; positive = over-forecast (risk of under-buying).
- Procurement buffer uses only errors from prior days (no look-ahead). Flat demand is a user input.



   cd backend
   python -m venv .venv
   source .venv/bin/activate       
   pip install -r requirements-dev.txt
   python scripts/fetch_data.py     
   pytest -q
   uvicorn app.main:app --reload    
   
   # API docs at http://localhost:8000/docs