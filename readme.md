# 🏦 ApexBank – Python Flask Banking System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-Flask%203.0-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%7C%20SQLite-blueviolet.svg)](https://www.postgresql.org/)
[![Deployment](https://img.shields.io/badge/Deploy-Vercel-black.svg)](https://vercel.com/)

A modern, full-stack banking mini-project built with **Python**, **Flask**, and **PostgreSQL**. Designed with single-file architecture for lightweight execution, zero-configuration local runs, and seamless serverless deployment on **Vercel**.

---

## 📌 Project Overview

ApexBank provides a clean, responsive web interface that simulates real-world core banking operations. It features real-time financial transactions, multi-account transfers, secure credential updates, and persistent relational database storage with automatic schema migrations.

---

## ✨ Features

- **Create Account**: Generates a unique 6-digit account number using Python's `random` module upon providing name, phone, 4-digit PIN, and optional initial deposit.
- **Secure Authentication**: Session-based login requiring both the 6-digit Account Number and 4-digit security PIN.
- **Check Balance**: Instant display of real-time balance.
- **Deposit Funds**: Validates amounts and increments account balance.
- **Withdraw Funds**: Includes strict balance and overdraft validation before deduction.
- **Transfer Money**: Atomically moves funds between two existing accounts with dual-entry transaction logging.
- **Transaction History**: Chronologically tracks operations (Deposits, Withdrawals, Transfers) with timestamps formatted via Python's `datetime` module.
- **Change PIN**: Updates the security PIN after verifying the existing PIN.
- **Dual Database Engine**: Connects natively to **PostgreSQL** (local or cloud like Neon, Supabase, Vercel Postgres) with an automatic zero-config fallback to **SQLite**.
- **Live Database Badge**: Dynamically displays the active storage engine (`🗄️ PostgreSQL` or `🗄️ SQLite`) in the navigation bar.
- **Logout**: Securely clears active sessions.

---

## 🛠️ Python Concepts & Modules Used

- **Modules:**
  - `random`: Dynamically generates collision-free 6-digit bank account numbers.
  - `datetime`: Timestamps all transaction logs and account creation records.
  - `psycopg2` / `sqlite3`: Manages relational database connections, parameterization, and transactions.
  - `flask`: Handles HTTP routing, request processing, sessions, flash messaging, and embedded template rendering.
- **Core Concepts:**
  - **Relational Data Modeling**: Foreign keys, transactions, and indexing across `accounts` and `transactions` tables.
  - **Single-File UI & CSS Design System**: Embedded modern glassmorphism UI with responsive CSS and CSS custom properties (no external static folders needed).
  - **Defensive Programming**: Validates input formats, positive monetary values, overdraft protection, and credential checks.

---

## 🗄️ Database Architecture

The application automatically provisions the following schema upon startup:

```sql
-- Accounts Table
CREATE TABLE IF NOT EXISTS accounts (
    account_no VARCHAR(6) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    pin VARCHAR(4) NOT NULL,
    balance NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    created_at VARCHAR(30)
);

-- Transactions Table
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    account_no VARCHAR(6) REFERENCES accounts(account_no) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    amount NUMERIC(14, 2) NOT NULL,
    details TEXT,
    balance NUMERIC(14, 2) NOT NULL,
    timestamp VARCHAR(30) NOT NULL
);
```

---

## 📁 Project Structure

```text
.
├── api/
│   └── index.py        # Core Flask backend, database manager & single-file web UI
├── .env.example        # Template for database connection string (DATABASE_URL)
├── .gitignore          # Excludes caches, virtual environments, and secrets
├── requirements.txt    # Python dependencies (Flask, psycopg2-binary)
├── vercel.json         # Vercel serverless rewrite configuration
└── README.md           # Project documentation
```

---

## 🚀 Getting Started (Local Setup)

### 1. Clone the Repository
```bash
git clone https://github.com/Manoj4143/Banking_System.git
cd Banking_System
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Database (Optional)
By default, the app automatically runs on a local SQLite database (`banking.db`). 

To connect to **PostgreSQL**, create a `.env` file in the project root:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/banking_db
```

### 4. Run the Application
```bash
python api/index.py
```

### 5. Access the Web App
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

---

## 🔑 Default Demo Account

For instant testing, a pre-seeded account is available:
- **Account Number:** `100001`
- **PIN:** `1234`
- **Initial Balance:** `$2,500.00`

---

## ☁️ Deploying to Vercel

1. Push your latest code to GitHub:
   ```bash
   git add .
   git commit -m "Update banking project"
   git push origin main
   ```
2. Go to [Vercel](https://vercel.com/) and click **"Add New Project"**.
3. Import your `Banking_System` repository.
4. *(Optional)* In **Project Settings > Environment Variables**, add:
   - `DATABASE_URL` = Your cloud PostgreSQL URL (from Neon, Supabase, or Vercel Postgres).
5. Click **Deploy**. Vercel will automatically build the serverless Python function in `api/index.py`.