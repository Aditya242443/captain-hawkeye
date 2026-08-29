# Captain Hawkeye (Project Plexis)

City-Wide AI Engine for Multi-Camera ANPR Trajectory Tracking and Urban Traffic Analytics — SIH 2026, PS 26127.

## Team
- **Abhinav Mishra** — ANPR + database + backend
- **Aditya Raj** — Trajectory tracking + traffic/heatmap
- **Aditya Pandey** — Alert system
- **Aashi Jain** — Frontend/dashboard

See `docs/api-contract.md` for the frozen API contract and `docs/db-schema.sql` for the database schema.

---

## Running the ANPR Backend Module Locally

### 1. Prerequisites & Environment Setup
Ensure you have Python 3.10+ installed.

```bash
# Clone the repository and navigate to the project root
git clone <repo-url>
cd captain-hawkeye

# Create and activate a virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and configure your Supabase/PostgreSQL database connection:

```bash
cp .env.example .env
```

Ensure `.env` contains:
```env
DATABASE_URL=postgresql://postgres:<password>@<host>:5432/postgres
```

### 3. Run the FastAPI Application
Start the backend server with Uvicorn:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

- API Docs / Swagger UI: `http://localhost:8000/docs`
- Redoc UI: `http://localhost:8000/redoc`
- ANPR Cameras: `http://localhost:8000/api/anpr/cameras`
- Recent Sightings: `http://localhost:8000/api/anpr/sightings/recent?limit=20`

### 4. Running Unit Tests
```bash
pytest backend/tests/test_anpr.py -v
```
