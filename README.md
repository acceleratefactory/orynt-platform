# ORYNT — Commerce Intelligence Platform

ORYNT is the intelligence layer for Nigerian SMEs. It sits on top of every tool a brand already uses — Paystack, Shopify, WooCommerce, WhatsApp, Meta Ads — collects their transaction, product, and customer data, scores every SKU and every customer, predicts what will happen next, and automates the right actions. Brand owners know exactly what to do with their money, products, and customers at any moment. Free for brands; monetised through institutional data access (fintechs, FMCG companies, suppliers).

---

## Project Structure

```
orynt-platform/
├── backend/        # FastAPI application (Python 3.11+)
├── frontend/       # Next.js 14 application (App Router)
├── docs/           # Master implementation strategy and sprint docs
├── .gitignore
└── README.md
```

---

## Backend Setup

**Requirements:** Python 3.11+, pip

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy the environment variable template and fill in real values:
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase, Redis, and JWT credentials
   ```

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

7. Verify the backend is running:
   ```
   GET http://localhost:8000/health
   Expected response: {"status": "ok", "database": "connected"}
   ```

---

## Frontend Setup

**Requirements:** Node.js 18+, npm

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Copy the environment variable template and fill in real values:
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your API URL and Supabase public keys
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```

5. Open your browser at `http://localhost:3000`

---

## Running Both Locally

1. Start the backend first (port 8000)
2. Start the frontend second (port 3000)
3. The frontend's `NEXT_PUBLIC_API_URL` in `.env.local` should point to `http://localhost:8000`
4. The frontend health check page will confirm the connection is working

---

## Environment Variables

**Never commit `.env` or `.env.local` files.** Use the `.env.example` templates as reference. Real credentials live only in your local `.env` files and in the Railway deployment environment settings.

- `backend/.env.example` — documents all required backend variables
- `frontend/.env.example` — documents all required frontend variables

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), Tailwind CSS, shadcn/ui, Recharts |
| Backend | Python 3.11, FastAPI, SQLAlchemy, Alembic, Celery |
| Database | PostgreSQL via Supabase |
| Cache / Queue | Redis via Upstash |
| Auth | Supabase Auth + JWT |
| Hosting | Railway.app |

---

*ORYNT — Sprint 0: Foundation*
