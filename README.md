# PROJECT KASHI 🏛️
### Enterprise Banking Management System
**Course:** Database Management Systems (B.Tech CSE - 3rd Semester)  
**Submission Date:** 28th October, 2026  
**Maximum Marks:** 10 Marks (Class Internal Assessment)  
**Technology Stack:** 3-Tier Architecture (Raw Semantic HTML5/CSS, Python Flask Backend, MySQL 8.0 Engine)

---

## 🌟 Project Overview
**Project Kashi** is a production-grade educational Banking Management System built to simulate enterprise database operations. Rather than acting as a standard CRUD application, it demonstrates real-world relational database design, data integrity, normalization, stored procedures, functions, triggers, and ACID-compliant transaction controls.

### 🏛️ The 3-Tier Architecture Flow
1. **Frontend (Presentation Layer):** Pure, semantic **HTML5** and custom modern **Vanilla CSS**. Uses forms, tables, status pills, and modal dialogs with zero heavy JavaScript frameworks (per assignment specifications).
2. **Backend (Application Layer):** **Python** with **Flask** managing HTTP routing, request validation, transaction coordination, and database communication.
3. **Database (Data Layer):** **MySQL 8.0** with InnoDB engine enforcing relational schemas, primary/foreign key constraints, check constraints, views, stored procedures, user-defined functions, and triggers.

---

## 📊 Relational Database Architecture (8 Tables)

| # | Table Name | Purpose & Primary Key | Key Foreign Keys & Constraints |
| :--- | :--- | :--- | :--- |
| 1 | **`BRANCH`** | Branch offices (`BranchID` PK) | `IFSCCode` (UNIQUE), `ContactNumber` |
| 2 | **`CUSTOMER`** | Bank customers (`CustomerID` PK) | `Mobile` (UNIQUE), `Email` (UNIQUE) |
| 3 | **`EMPLOYEE`** | Bank personnel (`EmployeeID` PK) | `BranchID` (FK), `Salary` (CHECK > 0) |
| 4 | **`ACCOUNT`** | Bank accounts (`AccountID` PK) | `AccountNumber` (UNIQUE), `Balance` (CHECK >= 0), `BranchID` (FK) |
| 5 | **`ACCOUNT_HOLDER`**| M:N Bridge (`CustomerID`, `AccountID` PK) | `CustomerID` (FK CASCADE), `AccountID` (FK CASCADE) |
| 6 | **`TRANSACTION`** | Financial ledger (`TransactionID` PK) | `AccountID` (FK), `Amount` (CHECK > 0), `ReferenceNumber` (UNIQUE) |
| 7 | **`LOAN`** | Sanctioned loans (`LoanID` PK) | `CustomerID` (FK), `BranchID` (FK), `LoanAmount` (CHECK > 0) |
| 8 | **`LOAN_PAYMENT`** | Loan installments (`PaymentID` PK) | `LoanID` (FK), `Amount` (CHECK > 0), `ReferenceNumber` (UNIQUE) |

---

## ⚡ Advanced DBMS Capabilities Demonstrated

### 1. ACID Transactions (`START TRANSACTION`, `COMMIT`, `ROLLBACK`)
- Handled inside Stored Procedure **`sp_transfer_funds`**.
- Acquires pessimistic row-level locks via `SELECT ... FOR UPDATE`.
- Deducts sender balance and increments beneficiary balance in a single atomic unit.
- If balance is insufficient or an account is inactive, it automatically executes `ROLLBACK`.

### 2. Stored Procedures & Functions
- **`sp_transfer_funds`**: Executes atomic inter-account money transfers.
- **`sp_deposit_money`**: Safely deposits funds and logs transactions.
- **`sp_withdraw_money`**: Validates available balance and debits accounts.
- **`fn_customer_total_balance(cust_id)`**: Calculates combined balance across all accounts held by a customer.
- **`fn_calculate_emi(P, r, N)`**: Computes monthly loan installments based on mathematical formula:
  $$\text{EMI} = \frac{P \cdot r \cdot (1 + r)^N}{(1 + r)^N - 1}$$

### 3. Database Triggers
- **`trg_prevent_negative_balance`**: Intercepts `BEFORE UPDATE ON ACCOUNT` and raises an error (`SQLSTATE '45000'`) if account balance drops below zero.
- **`trg_check_loan_completion`**: Automatically triggers `AFTER INSERT ON LOAN_PAYMENT` to sum total installments paid and update `LoanStatus = 'Closed'` once the loan is fully repaid.

### 4. Database Views (Virtual Tables)
- **`vw_customer_accounts`**: Joins Customer, Account, Account_Holder, and Branch.
- **`vw_passbook`**: Denormalized financial audit ledger with customer and branch details.
- **`vw_branch_summary`**: Branch-wise performance, accounts count, deposits, and loan exposure.

### 5. 10 Meaningful Business Problems (Interactive SQL Console)
Located on the `/analytics` route with real-time execution against MySQL:
1. Top 5 Highest-Balance Customers (`SUM()`, `JOIN`, `LIMIT`).
2. Branch Financial Health & Loan-to-Deposit Ratio (`LEFT JOIN`, `CASE`).
3. Inactive & Dormant Account Detection (`DATE_SUB()`, `HAVING`).
4. Multi-Product Customers (Savings + Active Loan) (`IN` Subquery).
5. High-Value Financial Audit (AML Compliance $\ge \text{₹}20,000$).
6. Branch Staff Productivity & Deposit Volume per Employee (`AVG()`, `NULLIF()`).
7. Loan Repayment Tracking & Outstanding Recovery (`COALESCE()`, `LEFT JOIN`).
8. Multi-Account Customers (`HAVING COUNT() > 1`, `GROUP_CONCAT()`).
9. Cash Inflow vs Outflow Turnover by Transaction Type (`CASE`, `GROUP BY`).
10. Geographic Customer Demographics & Penetration (`TIMESTAMPDIFF()`, `CURDATE()`).

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+ (Anaconda Python or standard Python)
- MySQL Server 8.0+ running on port 3306

### One-Click Launch (Windows)
Simply double-click the included batch launcher:
```bat
run.bat
```
This automatically initializes the MySQL database (`project_kashi`), executes `schema.sql`, seeds test data, and boots the Flask web application!

### Manual Setup
```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Setup Database
python database/setup_database.py

# 3. Start Flask Web Server
python backend/app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 📁 Repository Directory Structure

```
project-kashi/
├── backend/
│   ├── app.py                         # Main Flask application and API routes
│   ├── config.py                      # Application & database settings
│   ├── db.py                          # PyMySQL connection factory and helpers
│   └── requirements.txt               # Python package dependencies
├── database/
│   ├── schema.sql                     # Complete DDL & DML script (Tables, Views, SPs, Triggers)
│   ├── queries_10_business_problems.sql # 10 Business queries with comments
│   └── setup_database.py              # Automated DB initialization and seeding script
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css              # Custom modern vanilla CSS design system
│   │   └── js/
│   │       └── main.js                # Modals, tab controls, and client-side calculators
│   └── templates/
│       ├── base.html                  # Base template with navigation header and footer
│       ├── index.html                 # Executive dashboard with KPI cards
│       ├── customers.html             # Customer directory and registration modal
│       ├── customer_detail.html       # Individual customer profile and linked accounts
│       ├── accounts.html              # Account portfolio and open account modal
│       ├── transactions.html          # Passbook ledger and Operations hub (Transfer/Deposit/Withdraw)
│       ├── loans.html                 # Sanctioned loans, EMI calculator, and loan payment modal
│       ├── branches.html              # Branch network and employee roster
│       ├── sql_analytics.html         # Interactive 10 SQL business problems console
│       └── db_schema.html             # Relational schema inspector and Mermaid ER diagram
├── docs/
│   ├── PROJECT_REPORT.md              # Academic submission report (ERD, Normalization, DDL)
│   └── VIVA_PREPARATION_GUIDE.md      # Top 30+ Viva Questions & Answers for full marks
├── run.bat                            # Windows one-click launcher
├── .env.example                       # Sample environment configuration
└── README.md                          # Repository documentation
```

---

## 🎓 Viva Voce Preparation
Refer to [`docs/VIVA_PREPARATION_GUIDE.md`](file:///c:/Users/DELL/OneDrive/Desktop/project%20kashi/docs/VIVA_PREPARATION_GUIDE.md) for detailed explanations of:
- Why Many-to-Many requires the `ACCOUNT_HOLDER` bridge table.
- How `sp_transfer_funds` guarantees ACID properties and prevents race conditions with `FOR UPDATE`.
- Complete step-by-step proofs for 1NF, 2NF, 3NF, and BCNF normalization.
- Live demonstration checklist to score full 10/10 marks in class internal evaluation.
