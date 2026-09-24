import random
from datetime import datetime
from flask import Flask, request, redirect, url_for, session, render_template_string, flash

app = Flask(__name__)
app.secret_key = "banking-secret-key-super-secure"

# In-memory account database
# Format: { "account_number": { "name": ..., "phone": ..., "pin": ..., "balance": ..., "transactions": [...] } }
ACCOUNTS = {
    "100001": {
        "name": "Alex Morgan",
        "phone": "9876543210",
        "pin": "1234",
        "balance": 2500.0,
        "transactions": [
            {
                "type": "Initial Deposit",
                "amount": 2500.0,
                "details": "Opening Balance",
                "balance": 2500.0,
                "timestamp": "2026-09-20 10:30:00",
            }
        ],
    }
}


def generate_account_number():
    """Generate a unique 6-digit account number using the random module."""
    while True:
        acc_no = str(random.randint(100000, 999999))
        if acc_no not in ACCOUNTS:
            return acc_no


# Base modern HTML+CSS Template
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title if title else "ApexBank – Modern Banking" }}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 30, 49, 0.75);
            --card-border: rgba(255, 255, 255, 0.08);
            --primary: #4f46e5;
            --primary-hover: #4338ca;
            --primary-glow: rgba(79, 70, 229, 0.35);
            --accent: #06b6d4;
            --success: #10b981;
            --danger: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --input-bg: rgba(15, 23, 42, 0.8);
            --radius-lg: 16px;
            --radius-md: 10px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Plus Jakarta Sans', sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        body {
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(at 0% 0%, rgba(79, 70, 229, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(6, 182, 212, 0.12) 0px, transparent 50%),
                radial-gradient(at 50% 50%, rgba(15, 23, 42, 0.8) 0px, transparent 100%);
            min-height: 100vh;
            color: var(--text-main);
            display: flex;
            flex-direction: column;
        }

        .navbar {
            padding: 1.25rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--card-border);
            backdrop-filter: blur(12px);
            background: rgba(11, 15, 25, 0.6);
            position: sticky;
            top: 0;
            z-index: 50;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            text-decoration: none;
            color: var(--text-main);
            font-weight: 700;
            font-size: 1.25rem;
            letter-spacing: -0.02em;
        }

        .brand-icon {
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #4f46e5, #06b6d4);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            box-shadow: 0 4px 14px var(--primary-glow);
        }

        .nav-actions {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .user-pill {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            background: rgba(255, 255, 255, 0.05);
            padding: 0.4rem 0.9rem;
            border-radius: 30px;
            border: 1px solid var(--card-border);
            font-size: 0.875rem;
        }

        .dot-online {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--success);
            box-shadow: 0 0 8px var(--success);
        }

        .container {
            max-width: 1080px;
            margin: 2rem auto;
            padding: 0 1.5rem;
            width: 100%;
            flex: 1;
        }

        /* Flash Messages */
        .alerts {
            margin-bottom: 1.5rem;
        }

        .alert {
            padding: 0.9rem 1.25rem;
            border-radius: var(--radius-md);
            font-size: 0.9rem;
            font-weight: 500;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            animation: fadeIn 0.3s ease;
        }

        .alert-success {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #6ee7b7;
        }

        .alert-error {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #fca5a5;
        }

        .alert-info {
            background: rgba(79, 70, 229, 0.15);
            border: 1px solid rgba(79, 70, 229, 0.3);
            color: #a5b4fc;
        }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            padding: 0.7rem 1.3rem;
            border-radius: var(--radius-md);
            font-size: 0.9rem;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary), #3b82f6);
            color: #ffffff;
            box-shadow: 0 4px 16px var(--primary-glow);
        }

        .btn-primary:hover {
            opacity: 0.92;
            transform: translateY(-1px);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.06);
            color: var(--text-main);
            border: 1px solid var(--card-border);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.1);
        }

        .btn-danger {
            background: rgba(239, 68, 68, 0.15);
            color: #fca5a5;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .btn-danger:hover {
            background: rgba(239, 68, 68, 0.25);
        }

        .btn-sm {
            padding: 0.4rem 0.8rem;
            font-size: 0.8rem;
        }

        .btn-block {
            width: 100%;
        }

        /* Auth Form Cards */
        .auth-container {
            max-width: 440px;
            margin: 2.5rem auto;
        }

        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-lg);
            padding: 2rem;
            backdrop-filter: blur(16px);
            box-shadow: 0 16px 36px rgba(0, 0, 0, 0.4);
        }

        .card-header {
            margin-bottom: 1.5rem;
            text-align: center;
        }

        .card-title {
            font-size: 1.45rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }

        .card-subtitle {
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-top: 0.4rem;
        }

        /* Forms */
        .form-group {
            margin-bottom: 1.25rem;
        }

        .form-label {
            display: block;
            margin-bottom: 0.45rem;
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-muted);
        }

        .form-input {
            width: 100%;
            padding: 0.75rem 1rem;
            background: var(--input-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            color: var(--text-main);
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        .form-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px var(--primary-glow);
        }

        .form-hint {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 0.35rem;
        }

        /* Demo Account Banner */
        .demo-box {
            background: rgba(79, 70, 229, 0.08);
            border: 1px dashed rgba(79, 70, 229, 0.3);
            border-radius: var(--radius-md);
            padding: 0.9rem;
            margin-top: 1.25rem;
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .demo-box code {
            color: #a5b4fc;
            background: rgba(0, 0, 0, 0.3);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-family: monospace;
        }

        /* Dashboard Overview Grid */
        .overview-grid {
            display: grid;
            grid-template-columns: 1.3fr 1fr;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        @media (max-width: 768px) {
            .overview-grid {
                grid-template-columns: 1fr;
            }
        }

        .balance-card {
            background: linear-gradient(135deg, rgba(79, 70, 229, 0.25) 0%, rgba(6, 182, 212, 0.15) 100%), var(--card-bg);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: var(--radius-lg);
            padding: 2rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
            overflow: hidden;
        }

        .balance-card::after {
            content: "APEX";
            position: absolute;
            right: -10px;
            bottom: -20px;
            font-size: 7rem;
            font-weight: 900;
            color: rgba(255, 255, 255, 0.03);
            pointer-events: none;
        }

        .balance-label {
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .balance-value {
            font-size: 2.75rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin: 0.5rem 0 1.25rem 0;
            background: linear-gradient(to right, #ffffff, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .account-chip {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            font-size: 0.85rem;
            color: #cbd5e1;
        }

        .account-chip code {
            background: rgba(0, 0, 0, 0.4);
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-family: monospace;
            font-size: 0.95rem;
            letter-spacing: 0.05em;
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.2);
        }

        /* Quick Action Panels */
        .actions-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }

        .action-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 1.5rem;
            backdrop-filter: blur(12px);
        }

        .action-card h3 {
            font-size: 1.05rem;
            margin-bottom: 0.35rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .action-card p {
            color: var(--text-muted);
            font-size: 0.8rem;
            margin-bottom: 1rem;
        }

        /* History Table */
        .table-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-lg);
            overflow: hidden;
            backdrop-filter: blur(12px);
            margin-bottom: 2.5rem;
        }

        .table-header {
            padding: 1.25rem 1.75rem;
            border-bottom: 1px solid var(--card-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .table-title {
            font-size: 1.15rem;
            font-weight: 700;
        }

        .table-responsive {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.9rem;
        }

        th {
            padding: 1rem 1.75rem;
            color: var(--text-muted);
            font-weight: 600;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            background: rgba(15, 23, 42, 0.4);
            border-bottom: 1px solid var(--card-border);
        }

        td {
            padding: 1.1rem 1.75rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: #e2e8f0;
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr:hover td {
            background: rgba(255, 255, 255, 0.02);
        }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .badge-credit {
            background: rgba(16, 185, 129, 0.15);
            color: #6ee7b7;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .badge-debit {
            background: rgba(239, 68, 68, 0.15);
            color: #fca5a5;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .badge-neutral {
            background: rgba(148, 163, 184, 0.15);
            color: #cbd5e1;
            border: 1px solid rgba(148, 163, 184, 0.3);
        }

        .empty-history {
            padding: 3rem 1rem;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.9rem;
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 1.5rem;
            color: var(--text-muted);
            font-size: 0.8rem;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            margin-top: auto;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-4px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <a href="/" class="brand">
            <div class="brand-icon">🏦</div>
            <span>ApexBank</span>
        </a>
        <div class="nav-actions">
            {% if session.get('account_no') %}
                <div class="user-pill">
                    <span class="dot-online"></span>
                    <span>Acc: <strong>{{ session.get('account_no') }}</strong></span>
                </div>
                <a href="{{ url_for('logout') }}" class="btn btn-danger btn-sm">Logout</a>
            {% else %}
                <a href="{{ url_for('index') }}" class="btn btn-secondary btn-sm">Login</a>
                <a href="{{ url_for('register_view') }}" class="btn btn-primary btn-sm">Create Account</a>
            {% endif %}
        </div>
    </nav>

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

    <footer class="footer">
        <p>ApexBank System &bull; Minimal Python Flask on Vercel Serverless &bull; Safe &amp; Fast</p>
    </footer>
</body>
</html>
"""

LOGIN_REGISTER_TEMPLATE = (
    BASE_TEMPLATE.replace(
        "{% block content %}{% endblock %}",
        """
    <div class="auth-container">
        <div class="card">
            {% if mode == 'register' %}
                <div class="card-header">
                    <h2 class="card-title">Open New Account</h2>
                    <p class="card-subtitle">Generate a 6-digit account and start banking in seconds</p>
                </div>
                <form method="POST" action="{{ url_for('create_account') }}">
                    <div class="form-group">
                        <label class="form-label">Full Name</label>
                        <input type="text" name="name" class="form-input" placeholder="e.g. John Doe" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Phone Number</label>
                        <input type="tel" name="phone" class="form-input" placeholder="e.g. 9876543210" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Security PIN (4-Digits)</label>
                        <input type="password" name="pin" maxlength="4" pattern="[0-9]{4}" class="form-input" placeholder="••••" required>
                        <div class="form-hint">Must be exactly 4 numeric digits.</div>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Initial Deposit ($)</label>
                        <input type="number" step="0.01" min="0" name="initial_deposit" class="form-input" placeholder="0.00" value="0.00">
                    </div>
                    <button type="submit" class="btn btn-primary btn-block">Generate Account</button>
                    <div style="text-align: center; margin-top: 1.25rem; font-size: 0.85rem; color: var(--text-muted);">
                        Already have an account? <a href="{{ url_for('index') }}" style="color: #818cf8; text-decoration: none; font-weight: 600;">Sign in here</a>
                    </div>
                </form>
            {% else %}
                <div class="card-header">
                    <h2 class="card-title">Welcome Back</h2>
                    <p class="card-subtitle">Sign in to your ApexBank account</p>
                </div>
                <form method="POST" action="{{ url_for('login') }}">
                    <div class="form-group">
                        <label class="form-label">6-Digit Account Number</label>
                        <input type="text" name="account_no" class="form-input" placeholder="e.g. 100001" maxlength="6" pattern="[0-9]{6}" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">4-Digit PIN</label>
                        <input type="password" name="pin" maxlength="4" pattern="[0-9]{4}" class="form-input" placeholder="••••" required>
                    </div>
                    <button type="submit" class="btn btn-primary btn-block">Login to Account</button>
                    <div style="text-align: center; margin-top: 1.25rem; font-size: 0.85rem; color: var(--text-muted);">
                        New to ApexBank? <a href="{{ url_for('register_view') }}" style="color: #818cf8; text-decoration: none; font-weight: 600;">Create an account</a>
                    </div>
                </form>

                <div class="demo-box">
                    <strong>💡 Demo Test Account:</strong><br>
                    Account No: <code>100001</code> &bull; PIN: <code>1234</code>
                </div>
            {% endif %}
        </div>
    </div>
""",
    )
)

DASHBOARD_TEMPLATE = (
    BASE_TEMPLATE.replace(
        "{% block content %}{% endblock %}",
        """
    <!-- Overview Balance & Details -->
    <div class="overview-grid">
        <div class="balance-card">
            <div>
                <span class="balance-label">Available Balance</span>
                <div class="balance-value">${{ "%.2f"|format(account.balance) }}</div>
            </div>
            <div class="account-chip">
                <span>Account Number:</span>
                <code>{{ account_no }}</code>
                <span style="margin-left: auto; color: var(--text-muted); font-size: 0.8rem;">Status: <strong style="color: var(--success);">Active</strong></span>
            </div>
        </div>

        <div class="card" style="display: flex; flex-direction: column; justify-content: center;">
            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
                <div style="width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #4f46e5, #06b6d4); display: flex; align-items: center; justify-content: center; font-size: 1.25rem;">
                    👤
                </div>
                <div>
                    <h3 style="font-size: 1.15rem; font-weight: 700;">{{ account.name }}</h3>
                    <p style="color: var(--text-muted); font-size: 0.85rem;">Phone: {{ account.phone }}</p>
                </div>
            </div>
            <div style="background: rgba(15, 23, 42, 0.6); padding: 0.85rem; border-radius: 8px; font-size: 0.85rem; border: 1px solid var(--card-border);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.35rem;">
                    <span style="color: var(--text-muted);">Total Transactions:</span>
                    <strong>{{ account.transactions|length }}</strong>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: var(--text-muted);">Security Status:</span>
                    <span style="color: var(--success); font-weight: 600;">PIN Protected</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Quick Financial Action Cards -->
    <h2 style="font-size: 1.25rem; font-weight: 700; margin-bottom: 1rem;">Quick Actions</h2>
    <div class="actions-grid">
        <!-- Deposit Money -->
        <div class="action-card">
            <h3><span>📥</span> Deposit Funds</h3>
            <p>Add funds instantly into your bank balance.</p>
            <form method="POST" action="{{ url_for('deposit') }}">
                <div class="form-group">
                    <input type="number" step="0.01" min="0.01" name="amount" class="form-input" placeholder="Amount ($)" required>
                </div>
                <button type="submit" class="btn btn-primary btn-block">Deposit</button>
            </form>
        </div>

        <!-- Withdraw Money -->
        <div class="action-card">
            <h3><span>📤</span> Withdraw Funds</h3>
            <p>Withdraw money with real-time balance validation.</p>
            <form method="POST" action="{{ url_for('withdraw') }}">
                <div class="form-group">
                    <input type="number" step="0.01" min="0.01" name="amount" class="form-input" placeholder="Amount ($)" required>
                </div>
                <button type="submit" class="btn btn-secondary btn-block">Withdraw</button>
            </form>
        </div>

        <!-- Transfer Funds -->
        <div class="action-card">
            <h3><span>🔄</span> Transfer Money</h3>
            <p>Send funds to another 6-digit bank account.</p>
            <form method="POST" action="{{ url_for('transfer') }}">
                <div class="form-group" style="margin-bottom: 0.75rem;">
                    <input type="text" name="recipient_acc" class="form-input" placeholder="Recipient Acc # (6 digits)" maxlength="6" pattern="[0-9]{6}" required>
                </div>
                <div class="form-group">
                    <input type="number" step="0.01" min="0.01" name="amount" class="form-input" placeholder="Amount ($)" required>
                </div>
                <button type="submit" class="btn btn-primary btn-block">Send Transfer</button>
            </form>
        </div>

        <!-- Change PIN -->
        <div class="action-card">
            <h3><span>🔑</span> Change PIN</h3>
            <p>Update your 4-digit security PIN credentials.</p>
            <form method="POST" action="{{ url_for('change_pin') }}">
                <div class="form-group" style="margin-bottom: 0.75rem;">
                    <input type="password" name="old_pin" class="form-input" placeholder="Current PIN" maxlength="4" pattern="[0-9]{4}" required>
                </div>
                <div class="form-group">
                    <input type="password" name="new_pin" class="form-input" placeholder="New 4-Digit PIN" maxlength="4" pattern="[0-9]{4}" required>
                </div>
                <button type="submit" class="btn btn-secondary btn-block">Update PIN</button>
            </form>
        </div>
    </div>

    <!-- Transaction History Table -->
    <div class="table-card">
        <div class="table-header">
            <span class="table-title">📜 Transaction History</span>
            <span style="font-size: 0.8rem; color: var(--text-muted);">Timestamped via datetime module</span>
        </div>
        <div class="table-responsive">
            {% if account.transactions %}
                <table>
                    <thead>
                        <tr>
                            <th>Date &amp; Time</th>
                            <th>Operation Type</th>
                            <th>Description</th>
                            <th>Amount</th>
                            <th>Post Balance</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for tx in account.transactions|reverse %}
                            <tr>
                                <td style="color: var(--text-muted); font-size: 0.85rem;">{{ tx.timestamp }}</td>
                                <td>
                                    {% if 'Deposit' in tx.type or 'Received' in tx.type %}
                                        <span class="badge badge-credit">{{ tx.type }}</span>
                                    {% elif 'Withdraw' in tx.type or 'Sent' in tx.type %}
                                        <span class="badge badge-debit">{{ tx.type }}</span>
                                    {% else %}
                                        <span class="badge badge-neutral">{{ tx.type }}</span>
                                    {% endif %}
                                </td>
                                <td>{{ tx.details }}</td>
                                <td style="font-weight: 700; color: {% if 'Deposit' in tx.type or 'Received' in tx.type %}#6ee7b7{% elif 'Withdraw' in tx.type or 'Sent' in tx.type %}#fca5a5{% else %}#f8fafc{% endif %};">
                                    {% if 'Deposit' in tx.type or 'Received' in tx.type %}+{% elif 'Withdraw' in tx.type or 'Sent' in tx.type %}-{% endif %}${{ "%.2f"|format(tx.amount) }}
                                </td>
                                <td style="font-weight: 600;">${{ "%.2f"|format(tx.balance) }}</td>
                            </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <div class="empty-history">
                    No transactions recorded yet. Perform a deposit or transfer to see activity!
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
    if "account_no" in session and session["account_no"] in ACCOUNTS:
        return redirect(url_for("dashboard"))
    return render_template_string(
        LOGIN_REGISTER_TEMPLATE, mode="login", title="ApexBank – Login"
    )


@app.route("/register")
def register_view():
    if "account_no" in session and session["account_no"] in ACCOUNTS:
        return redirect(url_for("dashboard"))
    return render_template_string(
        LOGIN_REGISTER_TEMPLATE,
        mode="register",
        title="ApexBank – Open Account",
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

    # Auto-generate 6-digit account number using random module
    acc_no = generate_account_number()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ACCOUNTS[acc_no] = {
        "name": name,
        "phone": phone,
        "pin": pin,
        "balance": initial_deposit,
        "transactions": [
            {
                "type": "Account Created",
                "amount": initial_deposit,
                "details": "Opening Balance",
                "balance": initial_deposit,
                "timestamp": now_str,
            }
        ],
    }

    flash(
        f"🎉 Account successfully created! Your 6-Digit Account Number is {acc_no}. Please save it and sign in.",
        "success",
    )
    return redirect(url_for("index"))


@app.route("/login", methods=["POST"])
def login():
    acc_no = request.form.get("account_no", "").strip()
    pin = request.form.get("pin", "").strip()

    if not acc_no or not pin:
        flash("Account Number and PIN are required.", "error")
        return redirect(url_for("index"))

    account = ACCOUNTS.get(acc_no)
    if not account or account.get("pin") != pin:
        flash("Invalid Account Number or PIN. Please try again.", "error")
        return redirect(url_for("index"))

    session["account_no"] = acc_no
    flash(f"Welcome back, {account['name']}!", "success")
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    acc_no = session.get("account_no")
    if not acc_no or acc_no not in ACCOUNTS:
        session.pop("account_no", None)
        flash("Please log in to access your dashboard.", "info")
        return redirect(url_for("index"))

    account = ACCOUNTS[acc_no]
    return render_template_string(
        DASHBOARD_TEMPLATE,
        account=account,
        account_no=acc_no,
        title="ApexBank – Dashboard",
    )


@app.route("/deposit", methods=["POST"])
def deposit():
    acc_no = session.get("account_no")
    if not acc_no or acc_no not in ACCOUNTS:
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

    account = ACCOUNTS[acc_no]
    account["balance"] += amount
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    account["transactions"].append(
        {
            "type": "Deposit",
            "amount": amount,
            "details": "Cash / Online Deposit",
            "balance": account["balance"],
            "timestamp": now_str,
        }
    )

    flash(
        f"Successfully deposited ${amount:.2f}! New balance: ${account['balance']:.2f}",
        "success",
    )
    return redirect(url_for("dashboard"))


@app.route("/withdraw", methods=["POST"])
def withdraw():
    acc_no = session.get("account_no")
    if not acc_no or acc_no not in ACCOUNTS:
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

    account = ACCOUNTS[acc_no]
    if amount > account["balance"]:
        flash(
            f"Insufficient funds! You attempted to withdraw ${amount:.2f} but available balance is ${account['balance']:.2f}.",
            "error",
        )
        return redirect(url_for("dashboard"))

    account["balance"] -= amount
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    account["transactions"].append(
        {
            "type": "Withdrawal",
            "amount": amount,
            "details": "ATM / Counter Withdrawal",
            "balance": account["balance"],
            "timestamp": now_str,
        }
    )

    flash(
        f"Successfully withdrew ${amount:.2f}. Remaining balance: ${account['balance']:.2f}",
        "success",
    )
    return redirect(url_for("dashboard"))


@app.route("/transfer", methods=["POST"])
def transfer():
    acc_no = session.get("account_no")
    if not acc_no or acc_no not in ACCOUNTS:
        return redirect(url_for("index"))

    recipient_acc = request.form.get("recipient_acc", "").strip()
    amount_str = request.form.get("amount", "").strip()

    if recipient_acc == acc_no:
        flash("Cannot transfer money to your own account.", "error")
        return redirect(url_for("dashboard"))

    if recipient_acc not in ACCOUNTS:
        flash(
            f"Recipient account #{recipient_acc} not found in our banking registry.",
            "error",
        )
        return redirect(url_for("dashboard"))

    try:
        amount = float(amount_str)
        if amount <= 0:
            flash("Transfer amount must be greater than $0.00.", "error")
            return redirect(url_for("dashboard"))
    except ValueError:
        flash("Please enter a valid numeric amount.", "error")
        return redirect(url_for("dashboard"))

    sender = ACCOUNTS[acc_no]
    recipient = ACCOUNTS[recipient_acc]

    if amount > sender["balance"]:
        flash(
            f"Insufficient funds! Current balance: ${sender['balance']:.2f}, transfer requested: ${amount:.2f}.",
            "error",
        )
        return redirect(url_for("dashboard"))

    # Perform transfer
    sender["balance"] -= amount
    recipient["balance"] += amount
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sender["transactions"].append(
        {
            "type": "Transfer Sent",
            "amount": amount,
            "details": f"To Acc #{recipient_acc} ({recipient['name']})",
            "balance": sender["balance"],
            "timestamp": now_str,
        }
    )

    recipient["transactions"].append(
        {
            "type": "Transfer Received",
            "amount": amount,
            "details": f"From Acc #{acc_no} ({sender['name']})",
            "balance": recipient["balance"],
            "timestamp": now_str,
        }
    )

    flash(
        f"Transferred ${amount:.2f} to {recipient['name']} (#{recipient_acc}) successfully!",
        "success",
    )
    return redirect(url_for("dashboard"))


@app.route("/change-pin", methods=["POST"])
def change_pin():
    acc_no = session.get("account_no")
    if not acc_no or acc_no not in ACCOUNTS:
        return redirect(url_for("index"))

    old_pin = request.form.get("old_pin", "").strip()
    new_pin = request.form.get("new_pin", "").strip()

    account = ACCOUNTS[acc_no]
    if account["pin"] != old_pin:
        flash("Current PIN is incorrect.", "error")
        return redirect(url_for("dashboard"))

    if not new_pin.isdigit() or len(new_pin) != 4:
        flash("New PIN must be exactly 4 numeric digits.", "error")
        return redirect(url_for("dashboard"))

    if new_pin == old_pin:
        flash("New PIN must be different from current PIN.", "error")
        return redirect(url_for("dashboard"))

    account["pin"] = new_pin
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
