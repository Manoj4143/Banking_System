# 🏦 Banking System – Mini Project

A web-based mini project built with Python and Flask that simulates core banking operations. Designed for quick deployment on Vercel and version control via GitHub.

---

## 📌 Project Overview
This project provides a menu-driven banking application interface that allows users to register an account, log in securely, perform financial transactions, view transaction logs, and manage account credentials.

---

## ✨ Features
* **Create Account:** Generates a unique 6-digit account number upon providing full name, phone number, and a 4-digit PIN.
* **Secure Login:** Authenticates access using the generated Account Number and PIN.
* **Check Balance:** Displays real-time current account balance.
* **Deposit Money:** Adds specified funds to the account balance.
* **Withdraw Money:** Validates available funds before deducting specified amounts.
* **Transfer Money:** Transfers funds directly between two existing accounts.
* **Transaction History:** Displays chronologically logged account activities with exact timestamps.
* **Change PIN:** Allows updating the security PIN after verifying the old PIN.
* **Logout:** Terminates the active session and returns to the authentication menu.

---

## 🛠️ Python Concepts & Modules Used
* **Modules:**
  * `random`: Used to dynamically generate 6-digit account numbers.
  * `datetime`: Used to timestamp all deposit, withdrawal, and transfer events.
* **Core Concepts:**
  * **Variables & Data Types:** Handles floating-point balances, string credentials, and session state.
  * **Lists & Dictionaries:** Uses nested dictionaries for key-value account storage and lists for sequential history tracking.
  * **Functions & Routing:** Modularized HTTP route handlers for each banking operation.
  * **Conditional Statements:** Validates login credentials, withdrawal limits, and recipient account existence.

---

## 📁 Project Structure
```text
.
├── api/
│   └── index.py        # Core Python backend logic & web interface
├── requirements.txt    # Python dependencies
├── vercel.json         # Vercel deployment configuration
└── README.md           # Project documentation

🚀 Getting Started (Local Setup)
Clone the repository:

Bash
git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
cd YOUR_REPO_NAME
Install dependencies:

Bash
pip install -r requirements.txt
Run the application:

Bash
python api/index.py
Access the application:
Open http://127.0.0.1:5000 in your web browser.  