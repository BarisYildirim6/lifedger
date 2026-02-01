# lifedger 💸📊

**lifedger** is a self‑hosted personal accounting and expense‑tracking application.
It focuses on **manual expenses**, **OCR‑based receipt parsing**, and **recurring transactions** (subscriptions, rent, salary, etc.), all running in a **fully Dockerized environment**.

The project is designed to be:

* 🔒 Private (your data stays on your machine)
* 🧾 OCR‑powered (scan & parse receipts)
* 🔁 Recurring‑aware (materialized monthly expenses/income)
* 🐳 Docker‑first (easy local setup on Windows / macOS / Linux)

---

## ✨ Features

### Core

* Add and manage **expenses & income**
* Hierarchical **categories**
* Monthly & historical views

### OCR / Receipt Parsing

* Upload receipts (PDF / image)
* OCR via **Tesseract**
* Multi‑language support (EN / TR / DE / FR)
* Confidence scoring per receipt

### Recurring Transactions

* Define **recurring income or expenses**
* Supports:

  * Start date
  * Optional end date
  * Day of month (1–28 safe range)
  * Active / inactive state
* Recurring rules are **materialized into real expenses** via cron

### Infrastructure

* Flask + SQLAlchemy
* PostgreSQL
* Docker + Docker Compose
* Cron worker for background jobs

---

## 🧱 Architecture Overview

```
┌──────────────┐        ┌──────────────┐
│   Web App    │        │   Cron Worker│
│  (Flask)     │        │ (materialize │
│              │        │  recurring)  │
└──────┬───────┘        └──────┬───────┘
       │                       │
       └──────────┬────────────┘
                  │
            ┌─────▼─────┐
            │ PostgreSQL│
            └───────────┘
```

* **web**: Flask app (UI + API)
* **worker**: Runs cron jobs (recurring expenses, background tasks)
* **db**: PostgreSQL 15

---

## 🧰 Prerequisites

You only need **Docker** and **Docker Compose**.

### Windows

* Docker Desktop (WSL2 enabled)

### macOS

* Docker Desktop

### Linux

* Docker Engine
* docker‑compose plugin

Verify installation:

```bash
docker --version
docker compose version
```

---

## 🚀 Local Setup (All Platforms)

### 1️⃣ Clone the repository

```bash
git clone https://github.com/yourusername/lifedger.git
cd lifedger
```

### 2️⃣ Create environment file

```bash
cp .env.example .env
```

Edit `.env` if needed (defaults usually work):

```env
FLASK_APP=wsgi.py
FLASK_ENV=development
SECRET_KEY=secret-key
DATABASE_URL=postgresql+psycopg2://accounting:accounting@db:5432/accounting
```

---

### 3️⃣ Build and start containers

```bash
docker compose up --build
```

This will start:

* `web` → Flask app
* `worker` → cron container
* `db` → PostgreSQL

---

### 4️⃣ Initialize the database

In another terminal:

```bash
docker compose exec web flask db upgrade
```

(Optional) Seed data:

```bash
docker compose exec web flask seed
```

---

### 5️⃣ Open the app

Visit:

```
http://localhost:5000
```

---

## 🔁 Recurring Transactions – How It Works

1. You define a **recurring rule** (e.g. rent on day 5)
2. A **cron job** runs daily inside the `worker` container
3. If a rule should trigger today:

   * A real `Expense` record is created
   * Duplicate generation is prevented

### Key Fields

* `is_active`: toggle recurrence on/off
* `end_date`: optional (empty = continues indefinitely)

---

## ⏰ Cron & Background Jobs

Cron runs **inside Docker**, not on your host.

Example schedule (daily at 01:00):

```cron
0 1 * * * python /app/manage.py materialize-recurring
```

Logs:

```bash
docker compose logs worker
```

---

## 🧪 Development Tips

* Hot reload via mounted volume (`.:/app`)
* Flask logs visible in `web` container
* Cron isolated in `worker` container

Restart everything cleanly:

```bash
docker compose down -v
docker compose up --build
```

---

## 🗂️ Project Structure

```
lifedger/
├── app/
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── templates/
├── docker/
│   ├── flask/
│   │   └── Dockerfile
│   └── cron/
│       └── recurring-cron
├── migrations/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🛣️ Roadmap

* 📈 Monthly analytics & charts
* 🧠 Smarter OCR confidence heuristics
* 📱 Mobile‑friendly UI
* 🔐 Optional auth / multi‑user mode

---

## 🧡 License

MIT – do whatever you want, just don’t be evil.

---