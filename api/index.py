import os
import random
import sqlite3
from datetime import datetime
from flask import (
    Flask,
    request,
    redirect,
    url_for,
    session,
    render_template_string,
    flash,
)

# Optional dotenv loading for local development
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Optional psycopg2 import for PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "banking-secret-key-super-secure")

class PrefixMiddleware:
    """Normalize Vercel rewrite paths (/api/index or /api) to standard Flask routes."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        import urllib.parse
        qs = urllib.parse.parse_qs(environ.get("QUERY_STRING", ""))
        if "path" in qs and qs["path"][0]:
            target_path = qs["path"][0]
            while "//" in target_path:
                target_path = target_path.replace("//", "/")
            environ["PATH_INFO"] = target_path
        else:
            orig = (
                environ.get("HTTP_X_MATCHED_PATH")
                or environ.get("HTTP_X_FORWARDED_URI")
                or environ.get("RAW_URI")
            )
            if orig:
                clean = orig.split("?")[0]
                if clean and not clean.startswith("/api/index"):
                    environ["PATH_INFO"] = clean
                elif clean.startswith("/api/index"):
                    environ["PATH_INFO"] = clean[len("/api/index"):] or "/"
            else:
                path = environ.get("PATH_INFO", "")
                if path.startswith("/api/index"):
                    environ["PATH_INFO"] = path[len("/api/index"):] or "/"
                elif path.startswith("/api"):
                    environ["PATH_INFO"] = path[len("/api"):] or "/"
        return self.wsgi_app(environ, start_response)

app.wsgi_app = PrefixMiddleware(app.wsgi_app)

# Database URL detection (Vercel Postgres, Neon, Supabase, or local)
RAW_DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get(
    "POSTGRES_URL"
)
if RAW_DATABASE_URL and RAW_DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = RAW_DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    DATABASE_URL = RAW_DATABASE_URL

SQLITE_PATH = os.path.join(
    "/tmp" if os.environ.get("VERCEL") else ".", "banking.db"
)


class DatabaseManager:

    @staticmethod
    def get_connection():
        """Connect to PostgreSQL if configured, otherwise fallback to SQLite."""
        if DATABASE_URL and HAS_PSYCOPG2:
            try:
                conn = psycopg2.connect(DATABASE_URL)
                return conn, "PostgreSQL"
            except Exception as e:
                app.logger.warning(
                    f"PostgreSQL connection failed ({e}), falling back to SQLite."
                )

        # Fallback to local SQLite
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        return conn, "SQLite (Local)"

    @classmethod
    def get_db_type(cls):
        try:
            conn, db_type = cls.get_connection()
            conn.close()
            return db_type
        except Exception:
            return "Unavailable"

    @classmethod
    def init_db(cls):
        """Create tables if they do not exist and seed the demo account."""
        conn, db_type = cls.get_connection()
        cur = conn.cursor()
        is_pg = db_type == "PostgreSQL"

        if is_pg:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    account_no VARCHAR(6) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    phone VARCHAR(20) NOT NULL,
                    pin VARCHAR(4) NOT NULL,
                    balance NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
                    created_at VARCHAR(30)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    account_no VARCHAR(6) REFERENCES accounts(account_no) ON DELETE CASCADE,
                    type VARCHAR(50) NOT NULL,
                    amount NUMERIC(14, 2) NOT NULL,
                    details TEXT,
                    balance NUMERIC(14, 2) NOT NULL,
                    timestamp VARCHAR(30) NOT NULL
                );
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    account_no VARCHAR(6) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    phone VARCHAR(20) NOT NULL,
                    pin VARCHAR(4) NOT NULL,
                    balance REAL NOT NULL DEFAULT 0.00,
                    created_at VARCHAR(30)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_no VARCHAR(6) REFERENCES accounts(account_no) ON DELETE CASCADE,
                    type VARCHAR(50) NOT NULL,
                    amount REAL NOT NULL,
                    details TEXT,
                    balance REAL NOT NULL,
                    timestamp VARCHAR(30) NOT NULL
                );
            """)
        conn.commit()

        # Seed initial demo account if not exists
        check_q = (
            "SELECT account_no FROM accounts WHERE account_no = %s"
            if is_pg
            else "SELECT account_no FROM accounts WHERE account_no = ?"
        )
        cur.execute(check_q, ("100001",))
        if not cur.fetchone():
            ins_acc = (
                """
                INSERT INTO accounts (account_no, name, phone, pin, balance, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
                if is_pg
                else """
                INSERT INTO accounts (account_no, name, phone, pin, balance, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            )
            cur.execute(
                ins_acc,
                (
                    "100001",
                    "Alex Morgan",
                    "9876543210",
                    "1234",
                    2500.0,
                    "2026-09-20 10:30:00",
                ),
            )

            ins_tx = (
                """
                INSERT INTO transactions (account_no, type, amount, details, balance, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
                if is_pg
                else """
                INSERT INTO transactions (account_no, type, amount, details, balance, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            )
            cur.execute(
                ins_tx,
                (
                    "100001",
                    "Initial Deposit",
                    2500.0,
                    "Opening Balance",
                    2500.0,
                    "2026-09-20 10:30:00",
                ),
            )
            conn.commit()

        cur.close()
        conn.close()

    @classmethod
    def get_account_data(cls, account_no):
        conn, db_type = cls.get_connection()
        cur = conn.cursor()
        is_pg = db_type == "PostgreSQL"
        q = (
            "SELECT account_no, name, phone, pin, balance, created_at FROM accounts WHERE account_no = %s"
            if is_pg
            else "SELECT account_no, name, phone, pin, balance, created_at FROM accounts WHERE account_no = ?"
        )
        cur.execute(q, (account_no,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return None

        account = {
            "account_no": row[0],
            "name": row[1],
            "phone": row[2],
            "pin": row[3],
            "balance": float(row[4]),
            "created_at": row[5],
            "transactions": [],
        }

        tx_q = (
            "SELECT type, amount, details, balance, timestamp FROM transactions WHERE account_no = %s ORDER BY id DESC"
            if is_pg
            else "SELECT type, amount, details, balance, timestamp FROM transactions WHERE account_no = ? ORDER BY id DESC"
        )
        cur.execute(tx_q, (account_no,))
        tx_rows = cur.fetchall()
        for t in tx_rows:
            account["transactions"].append(
                {
                    "type": t[0],
                    "amount": float(t[1]),
                    "details": t[2],
                    "balance": float(t[3]),
                    "timestamp": t[4],
                }
            )

        cur.close()
        conn.close()
        return account

    @classmethod
    def generate_unique_account_number(cls):
        conn, db_type = cls.get_connection()
        cur = conn.cursor()
        is_pg = db_type == "PostgreSQL"
        q = (
            "SELECT 1 FROM accounts WHERE account_no = %s"
            if is_pg
            else "SELECT 1 FROM accounts WHERE account_no = ?"
        )
        while True:
            candidate = str(random.randint(100000, 999999))
            cur.execute(q, (candidate,))
            if not cur.fetchone():
                cur.close()
                conn.close()
                return candidate


# Initialize DB on launch
with app.app_context():
    try:
        DatabaseManager.init_db()
    except Exception as e:
        app.logger.error(f"Error during init_db: {e}")


# Neo-Fintech Kinetic Single-File Template
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title if title else "ApexBank – Neo-Fintech Kinetic" }}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            /* Neo-Fintech Kinetic Design Tokens */
            --surface-canvas: #f7f9ff;
            --surface-card: #ffffff;
            --surface-card-subtle: #f1f4f9;
            --surface-obsidian: #12161A;
            --primary-emerald: #064E3B;
            --primary-deep: #003527;
            --secondary-lime: #b1f818;
            --secondary-lime-dim: #9ad900;
            --secondary-lime-tint: rgba(177, 248, 24, 0.22);
            --tertiary-teal: #004d47;
            --text-dark: #181c20;
            --text-muted: #52605b;
            --border-hairline: rgba(24, 28, 32, 0.08);
            --border-dark-hairline: rgba(255, 255, 255, 0.12);
            
            --radius-pill: 9999px;
            --radius-card: 2rem;
            --radius-card-sm: 1.25rem;
            
            --shadow-subtle: 0 20px 40px -15px rgba(18, 22, 26, 0.06);
            --shadow-float: 0 25px 50px -12px rgba(6, 78, 59, 0.18);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Inter', sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        h1, h2, h3, h4, .font-display {
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        body {
            background-color: var(--surface-canvas);
            color: var(--text-dark);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        /* Top Navigation */
        .navbar {
            padding: 1.1rem 2.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(247, 249, 255, 0.85);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border-hairline);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            text-decoration: none;
            color: var(--primary-deep);
            font-size: 1.35rem;
            font-weight: 800;
            letter-spacing: -0.03em;
        }

        .brand-badge {
            width: 34px;
            height: 34px;
            background: var(--secondary-lime);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
            font-weight: 800;
            color: var(--primary-deep);
            box-shadow: 0 4px 12px rgba(177, 248, 24, 0.4);
        }

        .nav-links {
            display: flex;
            align-items: center;
            gap: 1.75rem;
            list-style: none;
        }

        @media (max-width: 900px) {
            .nav-links { display: none; }
            .navbar { padding: 1rem 1.25rem; }
        }

        .nav-link {
            text-decoration: none;
            color: var(--text-muted);
            font-size: 0.875rem;
            font-weight: 500;
            transition: color 0.2s;
        }

        .nav-link:hover {
            color: var(--primary-deep);
        }

        .nav-actions {
            display: flex;
            align-items: center;
            gap: 0.85rem;
        }

        .db-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.78rem;
            font-weight: 600;
            padding: 0.35rem 0.85rem;
            border-radius: var(--radius-pill);
            background: #eef8f3;
            color: var(--primary-emerald);
            border: 1px solid rgba(6, 78, 59, 0.15);
        }

        .dot-pulse {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--primary-emerald);
            box-shadow: 0 0 0 3px rgba(6, 78, 59, 0.18);
        }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            padding: 0.65rem 1.35rem;
            border-radius: var(--radius-pill);
            font-size: 0.875rem;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            border: none;
        }

        .btn-lime {
            background: var(--secondary-lime);
            color: var(--text-dark);
            font-weight: 700;
        }

        .btn-lime:hover {
            background: var(--secondary-lime-dim);
            transform: translateY(-1px);
            box-shadow: 0 8px 20px -4px rgba(177, 248, 24, 0.6);
        }

        .btn-forest {
            background: var(--primary-emerald);
            color: #ffffff;
        }

        .btn-forest:hover {
            background: #0b634c;
            transform: translateY(-1px);
            box-shadow: 0 8px 20px -4px rgba(6, 78, 59, 0.3);
        }

        .btn-ghost {
            background: transparent;
            color: var(--text-dark);
            border: 1px solid var(--border-hairline);
        }

        .btn-ghost:hover {
            background: rgba(0, 0, 0, 0.04);
        }

        .btn-danger {
            background: #ffebeb;
            color: #b91c1c;
            border: 1px solid rgba(185, 28, 28, 0.15);
        }

        .btn-danger:hover {
            background: #fecaca;
        }

        .btn-sm {
            padding: 0.4rem 0.9rem;
            font-size: 0.8rem;
        }

        .btn-block {
            width: 100%;
        }

        /* Main Container */
        .container {
            max-width: 1180px;
            margin: 2rem auto;
            padding: 0 1.5rem;
            width: 100%;
            flex: 1;
        }

        /* Alerts */
        .alerts {
            margin-bottom: 1.5rem;
        }

        .alert {
            padding: 0.85rem 1.25rem;
            border-radius: 1rem;
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.65rem;
            animation: fadeIn 0.3s ease;
        }

        .alert-success {
            background: #eefcf3;
            border: 1px solid #bbf2d0;
            color: #14532d;
        }

        .alert-error {
            background: #fef2f2;
            border: 1px solid #fecaca;
            color: #991b1b;
        }

        .alert-info {
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            color: #166534;
        }

        /* Hero Split View (Landing / Auth) */
        .hero-layout {
            display: grid;
            grid-template-columns: 1.15fr 1fr;
            gap: 3.5rem;
            align-items: center;
            margin-top: 1rem;
            margin-bottom: 3.5rem;
        }

        @media (max-width: 960px) {
            .hero-layout {
                grid-template-columns: 1fr;
                gap: 2.5rem;
            }
        }

        .hero-headline {
            font-size: 3.25rem;
            font-weight: 800;
            line-height: 1.1;
            letter-spacing: -0.035em;
            color: var(--text-dark);
            margin-bottom: 1.25rem;
        }

        @media (max-width: 600px) {
            .hero-headline { font-size: 2.35rem; }
        }

        .badge-pill-lime {
            display: inline-block;
            background: var(--secondary-lime);
            color: var(--primary-deep);
            padding: 0.15rem 0.75rem;
            border-radius: var(--radius-pill);
            box-decoration-break: clone;
            -webkit-box-decoration-break: clone;
        }

        .hero-subhead {
            font-size: 1.05rem;
            color: var(--text-muted);
            line-height: 1.6;
            margin-bottom: 2rem;
            max-width: 520px;
        }

        .tag-pills {
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem;
            margin-top: 2rem;
        }

        .tag-pill {
            padding: 0.35rem 0.85rem;
            background: var(--surface-card);
            border: 1px solid var(--border-hairline);
            border-radius: var(--radius-pill);
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--text-muted);
        }

        /* Form Card */
        .auth-card {
            background: var(--surface-card);
            border: 1px solid var(--border-hairline);
            border-radius: var(--radius-card);
            padding: 2.25rem;
            box-shadow: var(--shadow-subtle);
        }

        .form-group {
            margin-bottom: 1.15rem;
        }

        .form-label {
            display: block;
            margin-bottom: 0.45rem;
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-dark);
            letter-spacing: 0.01em;
        }

        .form-input-pill {
            width: 100%;
            padding: 0.75rem 1.25rem;
            background: var(--surface-card-subtle);
            border: 1px solid var(--border-hairline);
            border-radius: var(--radius-pill);
            color: var(--text-dark);
            font-size: 0.9rem;
            outline: none;
            transition: all 0.2s;
        }

        .form-input-pill:focus {
            background: #ffffff;
            border-color: var(--primary-emerald);
            box-shadow: 0 0 0 3px rgba(6, 78, 59, 0.12);
        }

        .demo-chip-box {
            background: #f7fceb;
            border: 1px dashed rgba(177, 248, 24, 0.8);
            border-radius: 14px;
            padding: 0.85rem;
            margin-top: 1.25rem;
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .demo-chip-box code {
            background: #ffffff;
            padding: 0.15rem 0.5rem;
            border-radius: 6px;
            font-family: monospace;
            font-weight: 700;
            color: var(--primary-deep);
            border: 1px solid var(--border-hairline);
        }

        /* Dashboard Obsidian Device Widget */
        .dashboard-hero-grid {
            display: grid;
            grid-template-columns: 1.25fr 1fr;
            gap: 1.75rem;
            margin-bottom: 2rem;
        }

        @media (max-width: 860px) {
            .dashboard-hero-grid {
                grid-template-columns: 1fr;
            }
        }

        .obsidian-card {
            background: var(--surface-obsidian);
            border-radius: var(--radius-card);
            padding: 2.25rem;
            color: #ffffff;
            box-shadow: 0 30px 60px -15px rgba(0, 0, 0, 0.35);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
            overflow: hidden;
        }

        .obsidian-card::before {
            content: "";
            position: absolute;
            top: -40%;
            right: -20%;
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(177, 248, 24, 0.12) 0%, transparent 70%);
            pointer-events: none;
        }

        .obsidian-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .currency-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(255, 255, 255, 0.08);
            padding: 0.35rem 0.8rem;
            border-radius: var(--radius-pill);
            font-size: 0.78rem;
            font-weight: 600;
            border: 1px solid var(--border-dark-hairline);
        }

        .balance-label {
            font-size: 0.8rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 1.5rem;
        }

        .numeric-balance {
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 3rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            font-variant-numeric: tabular-nums;
            margin: 0.35rem 0 1.5rem 0;
            color: #ffffff;
        }

        .action-dock {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex-wrap: wrap;
        }

        .dock-pill {
            background: rgba(255, 255, 255, 0.08);
            color: #ffffff;
            border: 1px solid var(--border-dark-hairline);
            padding: 0.45rem 1rem;
            border-radius: var(--radius-pill);
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }

        /* Profile & Security Card */
        .profile-card {
            background: var(--surface-card);
            border: 1px solid var(--border-hairline);
            border-radius: var(--radius-card);
            padding: 2rem;
            box-shadow: var(--shadow-subtle);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        /* Quick Action 4-Cards Grid */
        .actions-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2.25rem;
        }

        .action-card {
            background: var(--surface-card);
            border: 1px solid var(--border-hairline);
            border-radius: var(--radius-card-sm);
            padding: 1.5rem;
            box-shadow: var(--shadow-subtle);
            transition: transform 0.2s;
        }

        .action-card:hover {
            transform: translateY(-2px);
        }

        .action-card h3 {
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: var(--primary-deep);
        }

        .action-card p {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-bottom: 1.15rem;
        }

        /* Transaction Feed Card */
        .feed-card {
            background: var(--surface-card);
            border: 1px solid var(--border-hairline);
            border-radius: var(--radius-card);
            overflow: hidden;
            box-shadow: var(--shadow-subtle);
            margin-bottom: 2.5rem;
        }

        .feed-header {
            padding: 1.5rem 2rem;
            border-bottom: 1px solid var(--border-hairline);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .table-responsive {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }

        th {
            padding: 1rem 2rem;
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            background: #fafbfd;
            border-bottom: 1px solid var(--border-hairline);
        }

        td {
            padding: 1.15rem 2rem;
            border-bottom: 1px solid var(--border-hairline);
            font-size: 0.875rem;
            color: var(--text-dark);
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr:hover td {
            background: #fbfcfe;
        }

        .badge-credit {
            background: #eefcf3;
            color: var(--primary-emerald);
            border: 1px solid #bbf2d0;
            padding: 0.25rem 0.65rem;
            border-radius: var(--radius-pill);
            font-size: 0.75rem;
            font-weight: 700;
        }

        .badge-debit {
            background: #fdf2f2;
            color: #991b1b;
            border: 1px solid #fecaca;
            padding: 0.25rem 0.65rem;
            border-radius: var(--radius-pill);
            font-size: 0.75rem;
            font-weight: 700;
        }

        .amount-credit {
            color: var(--primary-emerald);
            font-weight: 700;
            font-variant-numeric: tabular-nums;
        }

        .amount-debit {
            color: var(--text-dark);
            font-weight: 700;
            font-variant-numeric: tabular-nums;
        }

        /* Footer */
        .footer {
            padding: 2rem;
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-muted);
            border-top: 1px solid var(--border-hairline);
            margin-top: auto;
            background: var(--surface-card);
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-4px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <!-- Top Navigation -->
    <nav class="navbar">
        <a href="/" class="brand">
            <div class="brand-badge">⚡</div>
            <span>ApexBank</span>
        </a>
        <ul class="nav-links">
            <li><a href="/" class="nav-link">Home</a></li>
            <li><a href="#features" class="nav-link">Features</a></li>
            <li><a href="#security" class="nav-link">Security</a></li>
        </ul>
        <div class="nav-actions">
            <div class="db-pill">
                <span class="dot-pulse"></span>
                <span>{{ db_type }}</span>
            </div>
            {% if session.get('account_no') %}
                <span style="font-size: 0.85rem; font-weight: 600;">Acc #{{ session.get('account_no') }}</span>
                <a href="{{ url_for('logout') }}" class="btn btn-danger btn-sm">Logout</a>
            {% else %}
                <a href="{{ url_for('index') }}" class="btn btn-ghost btn-sm">Log in</a>
                <a href="{{ url_for('register_view') }}" class="btn btn-lime btn-sm">Get Started</a>
            {% endif %}
        </div>
    </nav>

    <!-- Main Content Container -->
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="alerts">
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">
                            {% if category == 'success' %}
                                <span>✅</span>
                            {% elif category == 'error' %}
                                <span>⚠️</span>
                            {% else %}
                                <span>ℹ️</span>
                            {% endif %}
                            <span>{{ message }}</span>
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <!-- Minimalist Footer -->
    <footer class="footer">
        <p>ApexBank Neo-Fintech &bull; Engine: {{ db_type }} &bull; Institutional Security &amp; Kinetic Speed</p>
    </footer>
</body>
</html>
"""

LOGIN_REGISTER_TEMPLATE = (
    BASE_TEMPLATE.replace(
        "{% block content %}{% endblock %}",
        """
    <!-- New Account Created Pop-Up Modal -->
    {% if new_account %}
    <div id="credentialModal" style="position: fixed; inset: 0; background: rgba(18, 22, 26, 0.75); backdrop-filter: blur(8px); display: flex; align-items: center; justify-content: center; z-index: 9999; padding: 1.5rem; animation: fadeIn 0.3s ease;">
        <div style="background: #ffffff; border-radius: 2rem; max-width: 470px; width: 100%; padding: 2.5rem; box-shadow: 0 35px 70px -15px rgba(0,0,0,0.35); border: 1px solid rgba(24, 28, 32, 0.08); text-align: center; position: relative;">
            
            <div style="width: 60px; height: 60px; border-radius: 50%; background: #b1f818; display: inline-flex; align-items: center; justify-content: center; font-size: 1.85rem; margin-bottom: 1rem; box-shadow: 0 8px 24px rgba(177, 248, 24, 0.6);">
                🎉
            </div>

            <h2 style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.65rem; font-weight: 800; color: #003527; margin-bottom: 0.35rem;">
                Account Created!
            </h2>
            <p style="font-size: 0.875rem; color: #52605b; margin-bottom: 1.5rem;">
                Your account is ready in <strong>{{ db_type }}</strong>. Please copy and save your credentials:
            </p>

            <!-- Highlighted Credentials Box -->
            <div style="background: #f7f9ff; border: 1.5px solid rgba(6, 78, 59, 0.15); border-radius: 1.25rem; padding: 1.25rem; text-align: left; margin-bottom: 1.5rem;">
                
                <div style="margin-bottom: 1rem;">
                    <div style="font-size: 0.75rem; font-weight: 700; color: #52605b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.35rem;">
                        6-Digit Account Number
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #ffffff; padding: 0.75rem 1rem; border-radius: 12px; border: 1px solid rgba(24, 28, 32, 0.08);">
                        <span id="popupAccNo" style="font-family: 'Plus Jakarta Sans', monospace; font-size: 1.65rem; font-weight: 800; color: #003527; letter-spacing: 0.08em;">
                            {{ new_account.account_no }}
                        </span>
                        <button type="button" class="btn btn-sm btn-lime" onclick="copyAccNo('{{ new_account.account_no }}')" id="copyBtn">
                            📋 Copy
                        </button>
                    </div>
                </div>

                <div>
                    <div style="font-size: 0.75rem; font-weight: 700; color: #52605b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.35rem;">
                        4-Digit Security PIN
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #ffffff; padding: 0.75rem 1rem; border-radius: 12px; border: 1px solid rgba(24, 28, 32, 0.08);">
                        <span style="font-family: 'Plus Jakarta Sans', monospace; font-size: 1.45rem; font-weight: 800; color: #064E3B; letter-spacing: 0.15em;">
                            {{ new_account.pin }}
                        </span>
                        <span style="font-size: 0.75rem; color: #52605b; font-weight: 600;">(Keep PIN Private)</span>
                    </div>
                </div>

                <div style="margin-top: 1rem; padding-top: 0.75rem; border-top: 1px dashed rgba(24, 28, 32, 0.12); display: flex; justify-content: space-between; font-size: 0.85rem;">
                    <span style="color: #52605b;">Account Holder:</span>
                    <strong>{{ new_account.name }}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-top: 0.35rem;">
                    <span style="color: #52605b;">Initial Deposit:</span>
                    <strong style="color: #064E3B;">${{ "%.2f"|format(new_account.balance) }}</strong>
                </div>
            </div>

            <button type="button" class="btn btn-lime btn-block" style="padding: 0.9rem; font-size: 0.95rem;" onclick="dismissModal('{{ new_account.account_no }}')">
                Continue to Sign In &rarr;
            </button>
        </div>
    </div>

    <script>
        function copyAccNo(accNo) {
            navigator.clipboard.writeText(accNo).then(function() {
                var btn = document.getElementById('copyBtn');
                btn.innerText = '✅ Copied!';
                setTimeout(function() { btn.innerText = '📋 Copy'; }, 2000);
            });
        }

        function dismissModal(accNo) {
            var modal = document.getElementById('credentialModal');
            if (modal) modal.style.display = 'none';
            var accInput = document.querySelector('input[name="account_no"]');
            if (accInput) {
                accInput.value = accNo;
                var pinInput = document.querySelector('input[name="pin"]');
                if (pinInput) pinInput.focus();
            }
        }
    </script>
    {% endif %}

    <div class="hero-layout">
        <!-- Hero Editorial Left Column -->
        <div>
            <h1 class="hero-headline">
                Your Partner in Smarter <span class="badge-pill-lime">Financial Decisions</span>
            </h1>
            <p class="hero-subhead">
                Take control of your money with tools designed to help you save more, invest wisely, and plan ahead — effortlessly with bank-grade security.
            </p>
            
            <div style="display: flex; align-items: center; gap: 1rem;">
                {% if mode == 'register' %}
                    <a href="{{ url_for('index') }}" class="btn btn-ghost">Already have an account? Sign In</a>
                {% else %}
                    <a href="{{ url_for('register_view') }}" class="btn btn-lime">Open an Account &rarr;</a>
                {% endif %}
            </div>

            <div class="tag-pills">
                <span class="tag-pill">Market Insights</span>
                <span class="tag-pill">Zero Hidden Fees</span>
                <span class="tag-pill">Instant Transfers</span>
                <span class="tag-pill">PostgreSQL Engine</span>
                <span class="tag-pill">256-Bit Encryption</span>
            </div>
        </div>

        <!-- Right Column: Interactive Form & 3D Cards Metaphor -->
        <div>
            <div class="auth-card">
                {% if mode == 'register' %}
                    <h2 style="font-size: 1.45rem; font-weight: 800; margin-bottom: 0.35rem; color: var(--primary-deep);">Create Account</h2>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1.5rem;">Auto-generates a unique 6-digit bank account number</p>
                    
                    <form method="POST" action="{{ url_for('create_account') }}">
                        <div class="form-group">
                            <label class="form-label">Full Name</label>
                            <input type="text" name="name" class="form-input-pill" placeholder="e.g. Bianca Taylor" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Phone Number</label>
                            <input type="tel" name="phone" class="form-input-pill" placeholder="e.g. 9876543210" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Security PIN (4-Digits)</label>
                            <input type="password" name="pin" maxlength="4" pattern="[0-9]{4}" class="form-input-pill" placeholder="••••" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Initial Deposit ($)</label>
                            <input type="number" step="0.01" min="0" name="initial_deposit" class="form-input-pill" placeholder="0.00" value="0.00">
                        </div>
                        <button type="submit" class="btn btn-lime btn-block" style="padding: 0.85rem;">Generate Account</button>
                    </form>
                {% else %}
                    <h2 style="font-size: 1.45rem; font-weight: 800; margin-bottom: 0.35rem; color: var(--primary-deep);">Welcome Back</h2>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1.5rem;">Sign in to your ApexBank neo-account</p>

                    <form method="POST" action="{{ url_for('login') }}">
                        <div class="form-group">
                            <label class="form-label">6-Digit Account Number</label>
                            <input type="text" name="account_no" class="form-input-pill" placeholder="e.g. 100001" maxlength="6" pattern="[0-9]{6}" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">4-Digit Security PIN</label>
                            <input type="password" name="pin" maxlength="4" pattern="[0-9]{4}" class="form-input-pill" placeholder="••••" required>
                        </div>
                        <button type="submit" class="btn btn-lime btn-block" style="padding: 0.85rem;">Log In to Account</button>
                    </form>

                    <div class="demo-chip-box">
                        <strong>💡 Pre-Seeded Demo Account:</strong><br>
                        Account Number: <code>100001</code> &bull; PIN: <code>1234</code>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
""",
    )
)

DASHBOARD_TEMPLATE = (
    BASE_TEMPLATE.replace(
        "{% block content %}{% endblock %}",
        """
    <!-- Dashboard Hero Grid -->
    <div class="dashboard-hero-grid">
        <!-- Obsidian Dark Interactive Balance Card -->
        <div class="obsidian-card">
            <div class="obsidian-top">
                <div class="currency-chip">
                    <span>🇺🇸</span>
                    <span>US Dollar</span>
                </div>
                <div style="font-size: 0.8rem; color: #94a3b8;">
                    Acc: <code style="color: var(--secondary-lime); font-weight: 700; background: rgba(255,255,255,0.06); padding: 0.2rem 0.5rem; border-radius: 6px;">{{ account_no }}</code>
                </div>
            </div>

            <div>
                <div class="balance-label">Available Total Balance</div>
                <div class="numeric-balance">${{ "%.2f"|format(account.balance) }}</div>
            </div>

            <div class="action-dock">
                <span class="dock-pill"><span>⚏</span> Scan QR</span>
                <span class="dock-pill"><span>📥</span> Request</span>
                <span class="dock-pill"><span>🔄</span> Direct Wire</span>
                <span style="width: 32px; height: 32px; border-radius: 50%; background: var(--secondary-lime); color: var(--text-dark); display: inline-flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.1rem; margin-left: auto;">+</span>
            </div>
        </div>

        <!-- Profile & Account Details Card -->
        <div class="profile-card">
            <div>
                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.25rem;">
                    <div style="width: 48px; height: 48px; border-radius: 14px; background: #eef8f3; color: var(--primary-emerald); display: flex; align-items: center; justify-content: center; font-size: 1.4rem; font-weight: 800;">
                        👤
                    </div>
                    <div>
                        <h2 style="font-size: 1.25rem; font-weight: 800; color: var(--primary-deep);">{{ account.name }}</h2>
                        <p style="color: var(--text-muted); font-size: 0.85rem;">Phone: {{ account.phone }}</p>
                    </div>
                </div>

                <div style="background: var(--surface-card-subtle); padding: 1rem; border-radius: 1rem; border: 1px solid var(--border-hairline);">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.85rem;">
                        <span style="color: var(--text-muted);">Database Storage:</span>
                        <strong style="color: var(--primary-emerald);">{{ db_type }}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.85rem;">
                        <span style="color: var(--text-muted);">Account Activity:</span>
                        <strong>{{ account.transactions|length }} Events Logged</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                        <span style="color: var(--text-muted);">Security Standard:</span>
                        <span style="color: var(--primary-emerald); font-weight: 700;">PIN Encrypted</span>
                    </div>
                </div>
            </div>

            <div style="margin-top: 1.5rem; display: flex; gap: 0.75rem;">
                <span class="badge-credit" style="font-size: 0.8rem; padding: 0.4rem 0.9rem;">Verified Client</span>
                <span class="badge-credit" style="font-size: 0.8rem; padding: 0.4rem 0.9rem;">Tier 1 Liquid</span>
            </div>
        </div>
    </div>

    <!-- Quick Financial Actions Grid -->
    <h2 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 1rem; color: var(--primary-deep);">Financial Operations</h2>
    <div class="actions-grid">
        <!-- Deposit Money -->
        <div class="action-card">
            <h3><span>📥</span> Deposit Funds</h3>
            <p>Instantly credit funds to your balance.</p>
            <form method="POST" action="{{ url_for('deposit') }}">
                <div class="form-group">
                    <input type="number" step="0.01" min="0.01" name="amount" class="form-input-pill" placeholder="Amount ($)" required>
                </div>
                <button type="submit" class="btn btn-lime btn-block">Deposit</button>
            </form>
        </div>

        <!-- Withdraw Money -->
        <div class="action-card">
            <h3><span>📤</span> Withdraw Funds</h3>
            <p>Withdraw with overdraft protection.</p>
            <form method="POST" action="{{ url_for('withdraw') }}">
                <div class="form-group">
                    <input type="number" step="0.01" min="0.01" name="amount" class="form-input-pill" placeholder="Amount ($)" required>
                </div>
                <button type="submit" class="btn btn-forest btn-block">Withdraw</button>
            </form>
        </div>

        <!-- Transfer Funds -->
        <div class="action-card">
            <h3><span>🔄</span> Transfer Money</h3>
            <p>Direct wire to another 6-digit account.</p>
            <form method="POST" action="{{ url_for('transfer') }}">
                <div class="form-group" style="margin-bottom: 0.65rem;">
                    <input type="text" name="recipient_acc" class="form-input-pill" placeholder="Recipient Acc # (6 digits)" maxlength="6" pattern="[0-9]{6}" required>
                </div>
                <div class="form-group">
                    <input type="number" step="0.01" min="0.01" name="amount" class="form-input-pill" placeholder="Amount ($)" required>
                </div>
                <button type="submit" class="btn btn-lime btn-block">Send Transfer</button>
            </form>
        </div>

        <!-- Change PIN -->
        <div class="action-card">
            <h3><span>🔑</span> Security PIN</h3>
            <p>Update your 4-digit security PIN.</p>
            <form method="POST" action="{{ url_for('change_pin') }}">
                <div class="form-group" style="margin-bottom: 0.65rem;">
                    <input type="password" name="old_pin" class="form-input-pill" placeholder="Current PIN" maxlength="4" pattern="[0-9]{4}" required>
                </div>
                <div class="form-group">
                    <input type="password" name="new_pin" class="form-input-pill" placeholder="New PIN" maxlength="4" pattern="[0-9]{4}" required>
                </div>
                <button type="submit" class="btn btn-forest btn-block">Update PIN</button>
            </form>
        </div>
    </div>

    <!-- Transaction Ledger Table -->
    <div class="feed-card">
        <div class="feed-header">
            <div>
                <h3 style="font-size: 1.15rem; font-weight: 800; color: var(--primary-deep);">📜 Transaction Ledger</h3>
                <p style="font-size: 0.8rem; color: var(--text-muted);">Timestamped via Python datetime module</p>
            </div>
            <span class="db-pill">Live Ledger</span>
        </div>
        <div class="table-responsive">
            {% if account.transactions %}
                <table>
                    <thead>
                        <tr>
                            <th>Date &amp; Time</th>
                            <th>Operation</th>
                            <th>Description</th>
                            <th>Amount</th>
                            <th>Post Balance</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for tx in account.transactions %}
                            <tr>
                                <td style="color: var(--text-muted); font-size: 0.85rem;">{{ tx.timestamp }}</td>
                                <td>
                                    {% if 'Deposit' in tx.type or 'Received' in tx.type %}
                                        <span class="badge-credit">{{ tx.type }}</span>
                                    {% else %}
                                        <span class="badge-debit">{{ tx.type }}</span>
                                    {% endif %}
                                </td>
                                <td>{{ tx.details }}</td>
                                <td>
                                    {% if 'Deposit' in tx.type or 'Received' in tx.type %}
                                        <span class="amount-credit">+${{ "%.2f"|format(tx.amount) }}</span>
                                    {% else %}
                                        <span class="amount-debit">-${{ "%.2f"|format(tx.amount) }}</span>
                                    {% endif %}
                                </td>
                                <td style="font-weight: 600; font-variant-numeric: tabular-nums;">${{ "%.2f"|format(tx.balance) }}</td>
                            </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <div style="padding: 3rem; text-align: center; color: var(--text-muted); font-size: 0.9rem;">
                    No transactions recorded yet. Make a deposit to start your ledger!
                </div>
            {% endif %}
        </div>
    </div>
""",
    )
)


# Routes
@app.route("/")
def index():
    if "account_no" in session:
        acc = DatabaseManager.get_account_data(session["account_no"])
        if acc:
            return redirect(url_for("dashboard"))
        session.pop("account_no", None)

    # Check if a newly created account modal should be displayed
    new_account = session.pop("new_account_modal", None)

    return render_template_string(
        LOGIN_REGISTER_TEMPLATE,
        mode="login",
        title="ApexBank – Neo-Fintech Kinetic",
        db_type=DatabaseManager.get_db_type(),
        new_account=new_account,
    )


@app.route("/register")
def register_view():
    if "account_no" in session:
        acc = DatabaseManager.get_account_data(session["account_no"])
        if acc:
            return redirect(url_for("dashboard"))
        session.pop("account_no", None)

    return render_template_string(
        LOGIN_REGISTER_TEMPLATE,
        mode="register",
        title="ApexBank – Open Account",
        db_type=DatabaseManager.get_db_type(),
        new_account=None,
    )


@app.route("/create-account", methods=["POST"])
def create_account():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    pin = request.form.get("pin", "").strip()
    initial_deposit_str = request.form.get("initial_deposit", "0").strip()

    if not name or not phone:
        flash("Full Name and Phone Number are required.", "error")
        return redirect(url_for("register_view"))

    if not pin.isdigit() or len(pin) != 4:
        flash("PIN must be exactly 4 numeric digits.", "error")
        return redirect(url_for("register_view"))

    try:
        initial_deposit = (
            float(initial_deposit_str) if initial_deposit_str else 0.0
        )
        if initial_deposit < 0:
            flash("Initial deposit cannot be negative.", "error")
            return redirect(url_for("register_view"))
    except ValueError:
        flash("Invalid initial deposit amount.", "error")
        return redirect(url_for("register_view"))

    acc_no = DatabaseManager.generate_unique_account_number()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn, db_type = DatabaseManager.get_connection()
    cur = conn.cursor()
    is_pg = db_type == "PostgreSQL"

    ins_acc = (
        """
        INSERT INTO accounts (account_no, name, phone, pin, balance, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
        if is_pg
        else """
        INSERT INTO accounts (account_no, name, phone, pin, balance, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    )
    cur.execute(ins_acc, (acc_no, name, phone, pin, initial_deposit, now_str))

    ins_tx = (
        """
        INSERT INTO transactions (account_no, type, amount, details, balance, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
        if is_pg
        else """
        INSERT INTO transactions (account_no, type, amount, details, balance, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    )
    cur.execute(
        ins_tx,
        (
            acc_no,
            "Account Created",
            initial_deposit,
            "Opening Balance",
            initial_deposit,
            now_str,
        ),
    )
    conn.commit()
    cur.close()
    conn.close()

    # Store in session to trigger the credentials pop-up modal
    session["new_account_modal"] = {
        "account_no": acc_no,
        "pin": pin,
        "name": name,
        "balance": initial_deposit,
    }

    return redirect(url_for("index"))


@app.route("/login", methods=["POST"])
def login():
    acc_no = request.form.get("account_no", "").strip()
    pin = request.form.get("pin", "").strip()

    if not acc_no or not pin:
        flash("Account Number and PIN are required.", "error")
        return redirect(url_for("index"))

    account = DatabaseManager.get_account_data(acc_no)
    if not account or account.get("pin") != pin:
        flash("Invalid Account Number or PIN. Please try again.", "error")
        return redirect(url_for("index"))

    session["account_no"] = acc_no
    flash(f"Welcome back, {account['name']}!", "success")
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    acc_no = session.get("account_no")
    if not acc_no:
        flash("Please log in to access your dashboard.", "info")
        return redirect(url_for("index"))

    account = DatabaseManager.get_account_data(acc_no)
    if not account:
        session.pop("account_no", None)
        flash("Account not found. Please log in again.", "info")
        return redirect(url_for("index"))

    return render_template_string(
        DASHBOARD_TEMPLATE,
        account=account,
        account_no=acc_no,
        title="ApexBank – Dashboard",
        db_type=DatabaseManager.get_db_type(),
    )


@app.route("/deposit", methods=["POST"])
def deposit():
    acc_no = session.get("account_no")
    if not acc_no:
        return redirect(url_for("index"))

    amount_str = request.form.get("amount", "").strip()
    try:
        amount = float(amount_str)
        if amount <= 0:
            flash("Deposit amount must be greater than $0.00.", "error")
            return redirect(url_for("dashboard"))
    except ValueError:
        flash("Please enter a valid numeric amount.", "error")
        return redirect(url_for("dashboard"))

    conn, db_type = DatabaseManager.get_connection()
    cur = conn.cursor()
    is_pg = db_type == "PostgreSQL"

    cur.execute(
        "SELECT balance FROM accounts WHERE account_no = %s"
        if is_pg
        else "SELECT balance FROM accounts WHERE account_no = ?",
        (acc_no,),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return redirect(url_for("index"))

    current_balance = float(row[0])
    new_balance = current_balance + amount
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute(
        "UPDATE accounts SET balance = %s WHERE account_no = %s"
        if is_pg
        else "UPDATE accounts SET balance = ? WHERE account_no = ?",
        (new_balance, acc_no),
    )
    cur.execute(
        """
        INSERT INTO transactions (account_no, type, amount, details, balance, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
        if is_pg
        else """
        INSERT INTO transactions (account_no, type, amount, details, balance, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (acc_no, "Deposit", amount, "Cash / Online Deposit", new_balance, now_str),
    )
    conn.commit()
    cur.close()
    conn.close()

    flash(
        f"Successfully deposited ${amount:.2f}! New balance: ${new_balance:.2f}",
        "success",
    )
    return redirect(url_for("dashboard"))


@app.route("/withdraw", methods=["POST"])
def withdraw():
    acc_no = session.get("account_no")
    if not acc_no:
        return redirect(url_for("index"))

    amount_str = request.form.get("amount", "").strip()
    try:
        amount = float(amount_str)
        if amount <= 0:
            flash("Withdrawal amount must be greater than $0.00.", "error")
            return redirect(url_for("dashboard"))
    except ValueError:
        flash("Please enter a valid numeric amount.", "error")
        return redirect(url_for("dashboard"))

    conn, db_type = DatabaseManager.get_connection()
    cur = conn.cursor()
    is_pg = db_type == "PostgreSQL"

    cur.execute(
        "SELECT balance FROM accounts WHERE account_no = %s"
        if is_pg
        else "SELECT balance FROM accounts WHERE account_no = ?",
        (acc_no,),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return redirect(url_for("index"))

    current_balance = float(row[0])
    if amount > current_balance:
        cur.close()
        conn.close()
        flash(
            f"Insufficient funds! You attempted to withdraw ${amount:.2f} but available balance is ${current_balance:.2f}.",
            "error",
        )
        return redirect(url_for("dashboard"))

    new_balance = current_balance - amount
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute(
        "UPDATE accounts SET balance = %s WHERE account_no = %s"
        if is_pg
        else "UPDATE accounts SET balance = ? WHERE account_no = ?",
        (new_balance, acc_no),
    )
    cur.execute(
        """
        INSERT INTO transactions (account_no, type, amount, details, balance, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
        if is_pg
        else """
        INSERT INTO transactions (account_no, type, amount, details, balance, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            acc_no,
            "Withdrawal",
            amount,
            "ATM / Counter Withdrawal",
            new_balance,
            now_str,
        ),
    )
    conn.commit()
    cur.close()
    conn.close()

    flash(
        f"Successfully withdrew ${amount:.2f}. Remaining balance: ${new_balance:.2f}",
        "success",
    )
    return redirect(url_for("dashboard"))


@app.route("/transfer", methods=["POST"])
def transfer():
    acc_no = session.get("account_no")
    if not acc_no:
        return redirect(url_for("index"))

    recipient_acc = request.form.get("recipient_acc", "").strip()
    amount_str = request.form.get("amount", "").strip()

    if recipient_acc == acc_no:
        flash("Cannot transfer money to your own account.", "error")
        return redirect(url_for("dashboard"))

    try:
        amount = float(amount_str)
        if amount <= 0:
            flash("Transfer amount must be greater than $0.00.", "error")
            return redirect(url_for("dashboard"))
    except ValueError:
        flash("Please enter a valid numeric amount.", "error")
        return redirect(url_for("dashboard"))

    conn, db_type = DatabaseManager.get_connection()
    cur = conn.cursor()
    is_pg = db_type == "PostgreSQL"

    # Fetch sender
    cur.execute(
        "SELECT name, balance FROM accounts WHERE account_no = %s"
        if is_pg
        else "SELECT name, balance FROM accounts WHERE account_no = ?",
        (acc_no,),
    )
    sender = cur.fetchone()
    if not sender:
        cur.close()
        conn.close()
        return redirect(url_for("index"))

    # Fetch recipient
    cur.execute(
        "SELECT name, balance FROM accounts WHERE account_no = %s"
        if is_pg
        else "SELECT name, balance FROM accounts WHERE account_no = ?",
        (recipient_acc,),
    )
    recipient = cur.fetchone()
    if not recipient:
        cur.close()
        conn.close()
        flash(
            f"Recipient account #{recipient_acc} not found in our banking registry.",
            "error",
        )
        return redirect(url_for("dashboard"))

    sender_name, sender_balance = sender[0], float(sender[1])
    recipient_name, recipient_balance = recipient[0], float(recipient[1])

    if amount > sender_balance:
        cur.close()
        conn.close()
        flash(
            f"Insufficient funds! Current balance: ${sender_balance:.2f}, transfer requested: ${amount:.2f}.",
            "error",
        )
        return redirect(url_for("dashboard"))

    # Execute transfer transactionally
    new_sender_bal = sender_balance - amount
    new_recipient_bal = recipient_balance + amount
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute(
        "UPDATE accounts SET balance = %s WHERE account_no = %s"
        if is_pg
        else "UPDATE accounts SET balance = ? WHERE account_no = ?",
        (new_sender_bal, acc_no),
    )
    cur.execute(
        "UPDATE accounts SET balance = %s WHERE account_no = %s"
        if is_pg
        else "UPDATE accounts SET balance = ? WHERE account_no = ?",
        (new_recipient_bal, recipient_acc),
    )

    cur.execute(
        """
        INSERT INTO transactions (account_no, type, amount, details, balance, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
        if is_pg
        else """
        INSERT INTO transactions (account_no, type, amount, details, balance, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            acc_no,
            "Transfer Sent",
            amount,
            f"To Acc #{recipient_acc} ({recipient_name})",
            new_sender_bal,
            now_str,
        ),
    )

    cur.execute(
        """
        INSERT INTO transactions (account_no, type, amount, details, balance, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
        if is_pg
        else """
        INSERT INTO transactions (account_no, type, amount, details, balance, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            recipient_acc,
            "Transfer Received",
            amount,
            f"From Acc #{acc_no} ({sender_name})",
            new_recipient_bal,
            now_str,
        ),
    )

    conn.commit()
    cur.close()
    conn.close()

    flash(
        f"Transferred ${amount:.2f} to {recipient_name} (#{recipient_acc}) successfully!",
        "success",
    )
    return redirect(url_for("dashboard"))


@app.route("/change-pin", methods=["POST"])
def change_pin():
    acc_no = session.get("account_no")
    if not acc_no:
        return redirect(url_for("index"))

    old_pin = request.form.get("old_pin", "").strip()
    new_pin = request.form.get("new_pin", "").strip()

    conn, db_type = DatabaseManager.get_connection()
    cur = conn.cursor()
    is_pg = db_type == "PostgreSQL"

    cur.execute(
        "SELECT pin FROM accounts WHERE account_no = %s"
        if is_pg
        else "SELECT pin FROM accounts WHERE account_no = ?",
        (acc_no,),
    )
    row = cur.fetchone()
    if not row or row[0] != old_pin:
        cur.close()
        conn.close()
        flash("Current PIN is incorrect.", "error")
        return redirect(url_for("dashboard"))

    if not new_pin.isdigit() or len(new_pin) != 4:
        cur.close()
        conn.close()
        flash("New PIN must be exactly 4 numeric digits.", "error")
        return redirect(url_for("dashboard"))

    if new_pin == old_pin:
        cur.close()
        conn.close()
        flash("New PIN must be different from current PIN.", "error")
        return redirect(url_for("dashboard"))

    cur.execute(
        "UPDATE accounts SET pin = %s WHERE account_no = %s"
        if is_pg
        else "UPDATE accounts SET pin = ? WHERE account_no = ?",
        (new_pin, acc_no),
    )
    conn.commit()
    cur.close()
    conn.close()

    flash("Security PIN updated successfully!", "success")
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.pop("account_no", None)
    flash("You have been securely logged out.", "info")
    return redirect(url_for("index"))


# For local testing
if __name__ == "__main__":
    app.run(debug=True, port=5000)
