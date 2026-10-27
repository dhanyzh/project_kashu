import os
import sys
import random
import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

# Add parent directory to sys.path so backend imports work properly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.config import Config
from backend.db import get_connection, query_db, execute_db

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "frontend", "templates"),
    static_folder=os.path.join(BASE_DIR, "frontend", "static")
)
app.config.from_object(Config)

# --------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------
def generate_account_number():
    """Generate a unique 10-digit bank account number."""
    return f"100100{random.randint(1000, 9999)}"

def generate_reference_number(prefix="TXN"):
    """Generate unique financial transaction reference number."""
    return f"{prefix}-{int(time.time())}-{random.randint(100, 999)}"

# --------------------------------------------------------------------
# 1. Dashboard Route
# --------------------------------------------------------------------
@app.route("/")
def dashboard():
    """
    Main Bank Overview Dashboard.
    Fetches key metrics, recent transactions, and branch portfolio summary.
    """
    try:
        # Aggregated KPI Metrics
        total_customers = query_db("SELECT COUNT(*) AS count FROM CUSTOMER;", one=True)['count']
        total_accounts = query_db("SELECT COUNT(*) AS count FROM ACCOUNT WHERE Status = 'Active';", one=True)['count']
        total_deposits = query_db("SELECT COALESCE(SUM(Balance), 0.00) AS total FROM ACCOUNT WHERE Status = 'Active';", one=True)['total']
        active_loans = query_db("SELECT COUNT(*) AS count FROM LOAN WHERE LoanStatus IN ('Approved', 'Disbursed');", one=True)['count']
        total_loan_amount = query_db("SELECT COALESCE(SUM(LoanAmount), 0.00) AS total FROM LOAN WHERE LoanStatus IN ('Approved', 'Disbursed');", one=True)['total']
        total_branches = query_db("SELECT COUNT(*) AS count FROM BRANCH;", one=True)['count']

        # Recent 6 transactions using the view
        recent_transactions = query_db("""
            SELECT * FROM vw_passbook 
            ORDER BY TransactionDate DESC 
            LIMIT 6;
        """)

        # Branch overview using vw_branch_summary
        branch_summaries = query_db("SELECT * FROM vw_branch_summary ORDER BY TotalDeposits DESC;")

        stats = {
            "total_customers": total_customers,
            "total_accounts": total_accounts,
            "total_deposits": total_deposits,
            "active_loans": active_loans,
            "total_loan_amount": total_loan_amount,
            "total_branches": total_branches
        }

        return render_template(
            "index.html",
            stats=stats,
            recent_transactions=recent_transactions,
            branch_summaries=branch_summaries,
            active_page="dashboard"
        )
    except Exception as e:
        flash(f"Database error loading dashboard: {str(e)}", "danger")
        return render_template("index.html", stats={}, recent_transactions=[], branch_summaries=[], active_page="dashboard")

# --------------------------------------------------------------------
# 2. Customers Routes
# --------------------------------------------------------------------
@app.route("/customers")
def customers_list():
    """
    Customer Directory with search functionality.
    """
    search = request.args.get("search", "").strip()
    if search:
        customers = query_db("""
            SELECT c.*, 
                   COUNT(ah.AccountID) AS TotalAccounts,
                   COALESCE(SUM(a.Balance), 0.00) AS TotalBalance
            FROM CUSTOMER c
            LEFT JOIN ACCOUNT_HOLDER ah ON c.CustomerID = ah.CustomerID
            LEFT JOIN ACCOUNT a ON ah.AccountID = a.AccountID
            WHERE c.FirstName LIKE %s OR c.LastName LIKE %s OR c.Email LIKE %s OR c.Mobile LIKE %s OR c.City LIKE %s
            GROUP BY c.CustomerID
            ORDER BY c.RegistrationDate DESC;
        """, (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        customers = query_db("""
            SELECT c.*, 
                   COUNT(ah.AccountID) AS TotalAccounts,
                   COALESCE(SUM(a.Balance), 0.00) AS TotalBalance
            FROM CUSTOMER c
            LEFT JOIN ACCOUNT_HOLDER ah ON c.CustomerID = ah.CustomerID
            LEFT JOIN ACCOUNT a ON ah.AccountID = a.AccountID
            GROUP BY c.CustomerID
            ORDER BY c.RegistrationDate DESC;
        """)

    return render_template("customers.html", customers=customers, search=search, active_page="customers")

@app.route("/customers/<int:cust_id>")
def customer_detail(cust_id):
    """
    Individual Customer Profile showing:
    - Personal info
    - Stored function total balance calculation
    - Linked accounts
    - Active loans & repayments
    """
    customer = query_db("SELECT * FROM CUSTOMER WHERE CustomerID = %s;", (cust_id,), one=True)
    if not customer:
        flash("Customer not found.", "warning")
        return redirect(url_for("customers_list"))

    # Call Stored Function fn_customer_total_balance
    total_balance_res = query_db("SELECT fn_customer_total_balance(%s) AS TotalBalance;", (cust_id,), one=True)
    total_balance = total_balance_res['TotalBalance'] if total_balance_res else 0.00

    # Linked accounts
    accounts = query_db("""
        SELECT a.*, b.BranchName, b.IFSCCode, ah.HolderType, ah.HolderSince
        FROM ACCOUNT a
        JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID
        JOIN BRANCH b ON a.BranchID = b.BranchID
        WHERE ah.CustomerID = %s;
    """, (cust_id,))

    # Loans
    loans = query_db("""
        SELECT l.*, b.BranchName,
               COALESCE(SUM(lp.Amount), 0.00) AS TotalRepaid,
               fn_calculate_emi(l.LoanAmount, l.InterestRate, l.TenureMonths) AS MonthlyEMI
        FROM LOAN l
        JOIN BRANCH b ON l.BranchID = b.BranchID
        LEFT JOIN LOAN_PAYMENT lp ON l.LoanID = lp.LoanID
        WHERE l.CustomerID = %s
        GROUP BY l.LoanID;
    """, (cust_id,))

    return render_template(
        "customer_detail.html",
        customer=customer,
        total_balance=total_balance,
        accounts=accounts,
        loans=loans,
        active_page="customers"
    )

@app.route("/customers/register", methods=["POST"])
def customer_register():
    """
    Register a new customer in CUSTOMER table.
    """
    try:
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        dob = request.form.get("dob")
        gender = request.form.get("gender")
        mobile = request.form.get("mobile", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()

        if not (first_name and last_name and dob and gender and mobile and email and address and city):
            flash("All fields are mandatory for Customer Registration.", "warning")
            return redirect(url_for("customers_list"))

        execute_db("""
            INSERT INTO CUSTOMER (FirstName, LastName, DateOfBirth, Gender, Mobile, Email, Address, City)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """, (first_name, last_name, dob, gender, mobile, email, address, city))

        flash(f"Customer '{first_name} {last_name}' registered successfully!", "success")
    except Exception as e:
        flash(f"Failed to register customer: {str(e)}", "danger")

    return redirect(url_for("customers_list"))

# --------------------------------------------------------------------
# 3. Accounts Routes
# --------------------------------------------------------------------
@app.route("/accounts")
def accounts_list():
    """
    Display all Bank Accounts with owner information and branch details.
    """
    accounts = query_db("""
        SELECT a.*, b.BranchName, b.IFSCCode,
               c.CustomerID, CONCAT(c.FirstName, ' ', c.LastName) AS OwnerName, c.Mobile AS OwnerMobile,
               ah.HolderType
        FROM ACCOUNT a
        JOIN BRANCH b ON a.BranchID = b.BranchID
        LEFT JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID AND ah.HolderType = 'Primary'
        LEFT JOIN CUSTOMER c ON ah.CustomerID = c.CustomerID
        ORDER BY a.OpeningDate DESC, a.AccountID DESC;
    """)

    branches = query_db("SELECT BranchID, BranchName, IFSCCode FROM BRANCH ORDER BY BranchName;")
    customers = query_db("SELECT CustomerID, CONCAT(FirstName, ' ', LastName) AS FullName, Email, Mobile FROM CUSTOMER ORDER BY FirstName;")

    return render_template(
        "accounts.html",
        accounts=accounts,
        branches=branches,
        customers=customers,
        active_page="accounts"
    )

@app.route("/accounts/open", methods=["POST"])
def account_open():
    """
    Open a new Bank Account and map to CUSTOMER via ACCOUNT_HOLDER.
    Optionally process initial deposit transaction.
    """
    conn = get_connection()
    try:
        customer_id = int(request.form.get("customer_id"))
        branch_id = int(request.form.get("branch_id"))
        account_type = request.form.get("account_type")
        initial_deposit = float(request.form.get("initial_deposit", 0.0) or 0.0)
        account_number = generate_account_number()
        today = datetime.now().strftime("%Y-%m-%d")

        if initial_deposit < 0:
            flash("Initial deposit cannot be negative.", "warning")
            return redirect(url_for("accounts_list"))

        with conn.cursor() as cursor:
            # 1. Insert into ACCOUNT
            cursor.execute("""
                INSERT INTO ACCOUNT (AccountNumber, AccountType, OpeningDate, Balance, Status, BranchID)
                VALUES (%s, %s, %s, %s, 'Active', %s);
            """, (account_number, account_type, today, initial_deposit, branch_id))
            account_id = cursor.lastrowid

            # 2. Insert into ACCOUNT_HOLDER
            cursor.execute("""
                INSERT INTO ACCOUNT_HOLDER (CustomerID, AccountID, HolderSince, HolderType)
                VALUES (%s, %s, %s, 'Primary');
            """, (customer_id, account_id, today))

            # 3. If initial deposit > 0, log in TRANSACTION table
            if initial_deposit > 0:
                ref_num = generate_reference_number("TXN-INIT")
                cursor.execute("""
                    INSERT INTO TRANSACTION (AccountID, TransactionType, Amount, Description, ReferenceNumber, TransactionStatus)
                    VALUES (%s, 'DEPOSIT', %s, 'Initial Account Opening Deposit', %s, 'SUCCESS');
                """, (account_id, initial_deposit, ref_num))

            conn.commit()
            flash(f"Account #{account_number} created successfully with initial balance ₹{initial_deposit:,.2f}!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Failed to open account: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for("accounts_list"))

# --------------------------------------------------------------------
# 4. Transactions Routes (Deposit, Withdrawal, Transfer)
# --------------------------------------------------------------------
@app.route("/transactions")
def transactions_list():
    """
    Banking Operations & Transaction Passbook.
    Supports filtering by Account Number or Transaction Type.
    """
    acc_filter = request.args.get("account_number", "").strip()
    type_filter = request.args.get("txn_type", "").strip()

    sql = "SELECT * FROM vw_passbook WHERE 1=1"
    params = []

    if acc_filter:
        sql += " AND AccountNumber = %s"
        params.append(acc_filter)
    if type_filter:
        sql += " AND TransactionType = %s"
        params.append(type_filter)

    sql += " ORDER BY TransactionDate DESC LIMIT 100;"

    transactions = query_db(sql, params)
    active_accounts = query_db("""
        SELECT a.AccountID, a.AccountNumber, a.Balance, a.AccountType,
               CONCAT(c.FirstName, ' ', c.LastName) AS OwnerName
        FROM ACCOUNT a
        JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID AND ah.HolderType = 'Primary'
        JOIN CUSTOMER c ON ah.CustomerID = c.CustomerID
        WHERE a.Status = 'Active'
        ORDER BY a.AccountNumber;
    """)

    return render_template(
        "transactions.html",
        transactions=transactions,
        accounts=active_accounts,
        acc_filter=acc_filter,
        type_filter=type_filter,
        active_page="transactions"
    )

@app.route("/transactions/deposit", methods=["POST"])
def transaction_deposit():
    """
    Handle Deposit using stored procedure sp_deposit_money.
    """
    conn = get_connection()
    try:
        acc_id = int(request.form.get("account_id"))
        amount = float(request.form.get("amount", 0))
        description = request.form.get("description", "Cash Deposit")

        with conn.cursor() as cursor:
            # Call Stored Procedure
            cursor.execute("CALL sp_deposit_money(%s, %s, %s, @status_code, @status_msg);", (acc_id, amount, description))
            cursor.execute("SELECT @status_code AS code, @status_msg AS msg;")
            result = cursor.fetchone()
            
            if result and result['code'] == 200:
                flash(f"Deposit of ₹{amount:,.2f} completed successfully!", "success")
            else:
                flash(f"Deposit failed: {result['msg'] if result else 'Unknown error'}", "danger")
    except Exception as e:
        flash(f"Error executing deposit: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for("transactions_list"))

@app.route("/transactions/withdraw", methods=["POST"])
def transaction_withdraw():
    """
    Handle Withdrawal using stored procedure sp_withdraw_money.
    """
    conn = get_connection()
    try:
        acc_id = int(request.form.get("account_id"))
        amount = float(request.form.get("amount", 0))
        description = request.form.get("description", "ATM/Teller Withdrawal")

        with conn.cursor() as cursor:
            # Call Stored Procedure
            cursor.execute("CALL sp_withdraw_money(%s, %s, %s, @status_code, @status_msg);", (acc_id, amount, description))
            cursor.execute("SELECT @status_code AS code, @status_msg AS msg;")
            result = cursor.fetchone()

            if result and result['code'] == 200:
                flash(f"Withdrawal of ₹{amount:,.2f} completed successfully!", "success")
            else:
                flash(f"Withdrawal failed: {result['msg'] if result else 'Unknown error'}", "danger")
    except Exception as e:
        flash(f"Error executing withdrawal: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for("transactions_list"))

@app.route("/transactions/transfer", methods=["POST"])
def transaction_transfer():
    """
    Handle Atomic Fund Transfer using stored procedure sp_transfer_funds.
    Demonstrates ACID transactions: START TRANSACTION, COMMIT, and ROLLBACK.
    """
    conn = get_connection()
    try:
        sender_acc_id = int(request.form.get("sender_acc_id"))
        receiver_acc_id = int(request.form.get("receiver_acc_id"))
        amount = float(request.form.get("amount", 0))
        description = request.form.get("description", "Online Funds Transfer")

        with conn.cursor() as cursor:
            cursor.execute("""
                CALL sp_transfer_funds(%s, %s, %s, %s, @status_code, @status_msg);
            """, (sender_acc_id, receiver_acc_id, amount, description))
            cursor.execute("SELECT @status_code AS code, @status_msg AS msg;")
            result = cursor.fetchone()

            if result and result['code'] == 200:
                flash(f"Atomic Transfer of ₹{amount:,.2f} executed successfully! (ACID Commit applied)", "success")
            else:
                flash(f"Transfer failed: {result['msg'] if result else 'Transaction rolled back'}", "danger")
    except Exception as e:
        flash(f"Error executing transfer: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for("transactions_list"))

# --------------------------------------------------------------------
# 5. Loan Management Routes
# --------------------------------------------------------------------
@app.route("/loans")
def loans_list():
    """
    Loan Portfolio Management with EMI Calculation.
    """
    loans = query_db("""
        SELECT l.*, 
               CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName,
               c.Mobile,
               b.BranchName,
               COALESCE(SUM(lp.Amount), 0.00) AS TotalPaid,
               (l.LoanAmount - COALESCE(SUM(lp.Amount), 0.00)) AS OutstandingAmount,
               fn_calculate_emi(l.LoanAmount, l.InterestRate, l.TenureMonths) AS MonthlyEMI
        FROM LOAN l
        JOIN CUSTOMER c ON l.CustomerID = c.CustomerID
        JOIN BRANCH b ON l.BranchID = b.BranchID
        LEFT JOIN LOAN_PAYMENT lp ON l.LoanID = lp.LoanID
        GROUP BY l.LoanID
        ORDER BY l.StartDate DESC;
    """)

    customers = query_db("SELECT CustomerID, CONCAT(FirstName, ' ', LastName) AS FullName FROM CUSTOMER ORDER BY FirstName;")
    branches = query_db("SELECT BranchID, BranchName FROM BRANCH ORDER BY BranchName;")
    recent_payments = query_db("""
        SELECT lp.*, l.LoanType, CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName
        FROM LOAN_PAYMENT lp
        JOIN LOAN l ON lp.LoanID = l.LoanID
        JOIN CUSTOMER c ON l.CustomerID = c.CustomerID
        ORDER BY lp.PaymentDate DESC
        LIMIT 10;
    """)

    return render_template(
        "loans.html",
        loans=loans,
        customers=customers,
        branches=branches,
        recent_payments=recent_payments,
        active_page="loans"
    )

@app.route("/loans/apply", methods=["POST"])
def loan_apply():
    """
    Apply for a new loan.
    """
    try:
        customer_id = int(request.form.get("customer_id"))
        branch_id = int(request.form.get("branch_id"))
        loan_type = request.form.get("loan_type")
        loan_amount = float(request.form.get("loan_amount"))
        interest_rate = float(request.form.get("interest_rate"))
        tenure_months = int(request.form.get("tenure_months"))
        start_date = request.form.get("start_date") or datetime.now().strftime("%Y-%m-%d")

        execute_db("""
            INSERT INTO LOAN (CustomerID, BranchID, LoanType, LoanAmount, InterestRate, StartDate, TenureMonths, LoanStatus)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Disbursed');
        """, (customer_id, branch_id, loan_type, loan_amount, interest_rate, start_date, tenure_months))

        flash(f"{loan_type} of ₹{loan_amount:,.2f} sanctioned and disbursed successfully!", "success")
    except Exception as e:
        flash(f"Failed to sanction loan: {str(e)}", "danger")

    return redirect(url_for("loans_list"))

@app.route("/loans/pay", methods=["POST"])
def loan_payment():
    """
    Record payment against a loan.
    Trigger trg_check_loan_completion automatically updates LoanStatus to 'Closed' if fully repaid!
    """
    try:
        loan_id = int(request.form.get("loan_id"))
        amount = float(request.form.get("amount"))
        payment_mode = request.form.get("payment_mode", "NetBanking")
        ref_num = generate_reference_number("LPAY")

        execute_db("""
            INSERT INTO LOAN_PAYMENT (LoanID, Amount, PaymentMode, ReferenceNumber)
            VALUES (%s, %s, %s, %s);
        """, (loan_id, amount, payment_mode, ref_num))

        flash(f"Loan Repayment of ₹{amount:,.2f} recorded under Ref #{ref_num}! (Database Trigger evaluated)", "success")
    except Exception as e:
        flash(f"Failed to record loan payment: {str(e)}", "danger")

    return redirect(url_for("loans_list"))

# --------------------------------------------------------------------
# 6. Branches & Employees Routes
# --------------------------------------------------------------------
@app.route("/branches")
def branches_list():
    """
    View all bank branches, staff rosters, and financial aggregates.
    """
    branches = query_db("""
        SELECT b.*, 
               COUNT(DISTINCT a.AccountID) AS TotalAccounts,
               COALESCE(SUM(a.Balance), 0.00) AS TotalDeposits,
               COUNT(DISTINCT e.EmployeeID) AS TotalStaff
        FROM BRANCH b
        LEFT JOIN ACCOUNT a ON b.BranchID = a.BranchID AND a.Status = 'Active'
        LEFT JOIN EMPLOYEE e ON b.BranchID = e.BranchID
        GROUP BY b.BranchID
        ORDER BY b.BranchName;
    """)

    employees = query_db("""
        SELECT e.*, b.BranchName
        FROM EMPLOYEE e
        JOIN BRANCH b ON e.BranchID = b.BranchID
        ORDER BY e.JoiningDate DESC;
    """)

    return render_template(
        "branches.html",
        branches=branches,
        employees=employees,
        active_page="branches"
    )

@app.route("/branches/add", methods=["POST"])
def branch_add():
    """Add a new branch to BRANCH table."""
    try:
        branch_name = request.form.get("branch_name").strip()
        ifsc = request.form.get("ifsc_code").strip().upper()
        address = request.form.get("address").strip()
        city = request.form.get("city").strip()
        state = request.form.get("state").strip()
        contact = request.form.get("contact_number").strip()

        execute_db("""
            INSERT INTO BRANCH (BranchName, IFSCCode, Address, City, State, ContactNumber)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (branch_name, ifsc, address, city, state, contact))

        flash(f"Branch '{branch_name}' (IFSC: {ifsc}) created successfully!", "success")
    except Exception as e:
        flash(f"Failed to add branch: {str(e)}", "danger")

    return redirect(url_for("branches_list"))

@app.route("/employees/add", methods=["POST"])
def employee_add():
    """Add a new employee to EMPLOYEE table."""
    try:
        name = request.form.get("employee_name").strip()
        mobile = request.form.get("mobile").strip()
        email = request.form.get("email").strip()
        designation = request.form.get("designation").strip()
        salary = float(request.form.get("salary"))
        joining_date = request.form.get("joining_date")
        branch_id = int(request.form.get("branch_id"))

        execute_db("""
            INSERT INTO EMPLOYEE (EmployeeName, Mobile, Email, Designation, Salary, JoiningDate, BranchID)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (name, mobile, email, designation, salary, joining_date, branch_id))

        flash(f"Employee '{name}' added successfully!", "success")
    except Exception as e:
        flash(f"Failed to add employee: {str(e)}", "danger")

    return redirect(url_for("branches_list"))

# --------------------------------------------------------------------
# 7. SQL Analytics & 10 Business Problems Route
# --------------------------------------------------------------------
@app.route("/analytics")
def analytics():
    """
    Interactive Business Analytics Page:
    Directly answers the 10 real-world business questions required by the rubric.
    Executes live SQL queries against MySQL and shows results + DBMS concept tags.
    """
    selected_problem = int(request.args.get("problem", 1))

    problem_definitions = {
        1: {
            "title": "Problem 1: Top 5 Highest-Balance Customers",
            "business_question": "Identify the top 5 highest-balance customers across all their bank accounts for priority wealth banking relationship management.",
            "dbms_concepts": ["JOIN", "GROUP BY", "SUM() Aggregate", "ORDER BY", "LIMIT"],
            "sql": """
SELECT 
    c.CustomerID,
    CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName,
    c.Mobile,
    c.Email,
    c.City,
    COUNT(a.AccountID) AS TotalAccountsOwned,
    COALESCE(SUM(a.Balance), 0.00) AS TotalAggregateBalance
FROM CUSTOMER c
JOIN ACCOUNT_HOLDER ah ON c.CustomerID = ah.CustomerID
JOIN ACCOUNT a ON ah.AccountID = a.AccountID
WHERE a.Status = 'Active'
GROUP BY c.CustomerID, c.FirstName, c.LastName, c.Mobile, c.Email, c.City
ORDER BY TotalAggregateBalance DESC
LIMIT 5;
            """
        },
        2: {
            "title": "Problem 2: Branch Financial Health & Loan-to-Deposit Ratio",
            "business_question": "For each branch, compare total customer deposits against total loan disbursements to detect high-risk asset liability mismatches.",
            "dbms_concepts": ["Multi-table LEFT JOIN", "Derived Tables / Subqueries", "CASE Expression", "COALESCE"],
            "sql": """
SELECT 
    b.BranchID,
    b.BranchName,
    b.City,
    COALESCE(acc_data.TotalDeposits, 0.00) AS TotalDeposits,
    COALESCE(loan_data.TotalLoansDisbursed, 0.00) AS TotalLoansDisbursed,
    CASE 
        WHEN COALESCE(loan_data.TotalLoansDisbursed, 0.00) > COALESCE(acc_data.TotalDeposits, 0.00) 
        THEN 'HIGH EXPOSURE (Loans > Deposits)'
        ELSE 'BALANCED (Healthy Liquidity)'
    END AS LiquidityRiskStatus
FROM BRANCH b
LEFT JOIN (
    SELECT BranchID, SUM(Balance) AS TotalDeposits 
    FROM ACCOUNT 
    WHERE Status = 'Active' 
    GROUP BY BranchID
) acc_data ON b.BranchID = acc_data.BranchID
LEFT JOIN (
    SELECT BranchID, SUM(LoanAmount) AS TotalLoansDisbursed 
    FROM LOAN 
    WHERE LoanStatus IN ('Approved', 'Disbursed') 
    GROUP BY BranchID
) loan_data ON b.BranchID = loan_data.BranchID
ORDER BY TotalDeposits DESC;
            """
        },
        3: {
            "title": "Problem 3: Inactive / Dormant Account Detection",
            "business_question": "Find active accounts with zero transactions in the last 90 days (or never transacted) to issue re-KYC alerts.",
            "dbms_concepts": ["HAVING Clause", "LEFT JOIN", "DATE_SUB()", "NULL Handling"],
            "sql": """
SELECT 
    a.AccountID,
    a.AccountNumber,
    a.AccountType,
    a.Balance,
    CONCAT(c.FirstName, ' ', c.LastName) AS PrimaryHolder,
    c.Mobile,
    b.BranchName,
    MAX(t.TransactionDate) AS LastTransactionDate
FROM ACCOUNT a
JOIN BRANCH b ON a.BranchID = b.BranchID
JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID AND ah.HolderType = 'Primary'
JOIN CUSTOMER c ON ah.CustomerID = c.CustomerID
LEFT JOIN TRANSACTION t ON a.AccountID = t.AccountID
WHERE a.Status = 'Active'
GROUP BY a.AccountID, a.AccountNumber, a.AccountType, a.Balance, c.FirstName, c.LastName, c.Mobile, b.BranchName
HAVING LastTransactionDate IS NULL OR LastTransactionDate < DATE_SUB(NOW(), INTERVAL 90 DAY)
ORDER BY a.Balance DESC;
            """
        },
        4: {
            "title": "Problem 4: Multi-Product Customers (Savings + Active Loan)",
            "business_question": "Identify high-engagement customers holding both an active Savings account AND an active Loan for cross-sell benefits.",
            "dbms_concepts": ["Subqueries with IN", "Set Intersection Emulation", "Complex WHERE Filtering"],
            "sql": """
SELECT 
    c.CustomerID,
    CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName,
    c.Mobile,
    c.City,
    l.LoanType,
    l.LoanAmount,
    l.LoanStatus
FROM CUSTOMER c
JOIN LOAN l ON c.CustomerID = l.CustomerID
WHERE l.LoanStatus IN ('Approved', 'Disbursed')
  AND c.CustomerID IN (
      SELECT ah.CustomerID
      FROM ACCOUNT_HOLDER ah
      JOIN ACCOUNT a ON ah.AccountID = a.AccountID
      WHERE a.AccountType = 'Saving' AND a.Status = 'Active'
  );
            """
        },
        5: {
            "title": "Problem 5: High-Value Financial Audit (AML Compliance)",
            "business_question": "Retrieve all transactions of ₹20,000 or greater with full account, customer, and branch traceability for audit compliance.",
            "dbms_concepts": ["Multi-entity Joins", "Range Filtering", "Order by Amount"],
            "sql": """
SELECT 
    t.TransactionID,
    t.ReferenceNumber,
    t.TransactionDate,
    t.TransactionType,
    t.Amount,
    a.AccountNumber,
    CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName,
    b.BranchName,
    t.Description
FROM TRANSACTION t
JOIN ACCOUNT a ON t.AccountID = a.AccountID
JOIN BRANCH b ON a.BranchID = b.BranchID
JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID AND ah.HolderType = 'Primary'
JOIN CUSTOMER c ON ah.CustomerID = c.CustomerID
WHERE t.Amount >= 20000.00
ORDER BY t.Amount DESC;
            """
        },
        6: {
            "title": "Problem 6: Branch Staff Productivity & Deposit Volume per Employee",
            "business_question": "Compute the average staff salary per branch, employee count, and average customer deposit volume managed per employee.",
            "dbms_concepts": ["Calculated Columns", "NULLIF() Zero-division Protection", "AVG()", "COUNT(DISTINCT)"],
            "sql": """
SELECT 
    b.BranchID,
    b.BranchName,
    COUNT(DISTINCT e.EmployeeID) AS TotalStaff,
    ROUND(AVG(e.Salary), 2) AS AverageStaffSalary,
    COALESCE(SUM(DISTINCT a.Balance), 0.00) AS TotalBranchDeposits,
    ROUND(
        COALESCE(SUM(DISTINCT a.Balance), 0.00) / NULLIF(COUNT(DISTINCT e.EmployeeID), 0), 
        2
    ) AS DepositVolumePerEmployee
FROM BRANCH b
LEFT JOIN EMPLOYEE e ON b.BranchID = e.BranchID
LEFT JOIN ACCOUNT a ON b.BranchID = a.BranchID AND a.Status = 'Active'
GROUP BY b.BranchID, b.BranchName
ORDER BY TotalBranchDeposits DESC;
            """
        },
        7: {
            "title": "Problem 7: Loan Repayment Tracking & Outstanding Recovery",
            "business_question": "Determine the remaining principal and percentage repaid for each loan by summing all historical repayment installments.",
            "dbms_concepts": ["LEFT JOIN with Aggregation", "Mathematical Expressions", "ROUND()", "COALESCE()"],
            "sql": """
SELECT 
    l.LoanID,
    CONCAT(c.FirstName, ' ', c.LastName) AS BorrowerName,
    c.Mobile,
    l.LoanType,
    l.LoanAmount AS PrincipalAmount,
    l.InterestRate,
    COALESCE(SUM(lp.Amount), 0.00) AS TotalAmountRepaid,
    (l.LoanAmount - COALESCE(SUM(lp.Amount), 0.00)) AS OutstandingPrincipal,
    ROUND((COALESCE(SUM(lp.Amount), 0.00) / l.LoanAmount) * 100, 2) AS RepaymentPercentage,
    l.LoanStatus
FROM LOAN l
JOIN CUSTOMER c ON l.CustomerID = c.CustomerID
LEFT JOIN LOAN_PAYMENT lp ON l.LoanID = lp.LoanID
GROUP BY l.LoanID, c.FirstName, c.LastName, c.Mobile, l.LoanType, l.LoanAmount, l.InterestRate, l.LoanStatus
ORDER BY OutstandingPrincipal DESC;
            """
        },
        8: {
            "title": "Problem 8: Customers Holding Multiple Accounts (Cross-Selling)",
            "business_question": "List all customers who hold more than one account, their distinct account types, and total consolidated wealth.",
            "dbms_concepts": ["GROUP_CONCAT()", "HAVING COUNT() > 1", "Aggregate Functions"],
            "sql": """
SELECT 
    c.CustomerID,
    CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName,
    c.Mobile,
    COUNT(a.AccountID) AS TotalAccounts,
    GROUP_CONCAT(DISTINCT a.AccountType SEPARATOR ', ') AS AccountTypesHeld,
    SUM(a.Balance) AS TotalCombinedBalance
FROM CUSTOMER c
JOIN ACCOUNT_HOLDER ah ON c.CustomerID = ah.CustomerID
JOIN ACCOUNT a ON ah.AccountID = a.AccountID
GROUP BY c.CustomerID, c.FirstName, c.LastName, c.Mobile
HAVING COUNT(a.AccountID) > 1
ORDER BY TotalAccounts DESC;
            """
        },
        9: {
            "title": "Problem 9: Cash Inflow vs Outflow Turnover by Transaction Type",
            "business_question": "Summarize total monetary velocity: aggregate volume, average ticket size, and net liquidity impact categorized by transaction type.",
            "dbms_concepts": ["CASE Expression", "Turnover Aggregation", "AVG()", "WHERE Clause"],
            "sql": """
SELECT 
    t.TransactionType,
    COUNT(t.TransactionID) AS TotalTransactions,
    SUM(t.Amount) AS TotalTurnover,
    ROUND(AVG(t.Amount), 2) AS AverageTransactionSize,
    CASE 
        WHEN t.TransactionType IN ('DEPOSIT', 'TRANSFER_IN') THEN 'NET INFLOW (Liquidity Boost)'
        ELSE 'NET OUTFLOW (Fund Drain)'
    END AS CashFlowImpact
FROM TRANSACTION t
WHERE t.TransactionStatus = 'SUCCESS'
GROUP BY t.TransactionType
ORDER BY TotalTurnover DESC;
            """
        },
        10: {
            "title": "Problem 10: Geographic Customer Demographics & Penetration",
            "business_question": "Analyze banking penetration across cities: customer count, average customer age in years, and total deposits mobilized.",
            "dbms_concepts": ["TIMESTAMPDIFF()", "CURDATE()", "Demographic Aggregation", "GROUP BY City"],
            "sql": """
SELECT 
    c.City,
    COUNT(DISTINCT c.CustomerID) AS TotalCustomers,
    ROUND(AVG(TIMESTAMPDIFF(YEAR, c.DateOfBirth, CURDATE())), 1) AS AverageCustomerAge,
    COALESCE(SUM(a.Balance), 0.00) AS TotalCityDeposits
FROM CUSTOMER c
LEFT JOIN ACCOUNT_HOLDER ah ON c.CustomerID = ah.CustomerID
LEFT JOIN ACCOUNT a ON ah.AccountID = a.AccountID
GROUP BY c.City
ORDER BY TotalCityDeposits DESC;
            """
        }
    }

    current = problem_definitions.get(selected_problem, problem_definitions[1])
    try:
        results = query_db(current["sql"])
        columns = list(results[0].keys()) if results else []
    except Exception as e:
        results = []
        columns = []
        flash(f"SQL execution error: {str(e)}", "danger")

    return render_template(
        "sql_analytics.html",
        problems=problem_definitions,
        selected_id=selected_problem,
        current=current,
        columns=columns,
        results=results,
        active_page="analytics"
    )

# --------------------------------------------------------------------
# 8. Database Schema & Architecture Inspector Route
# --------------------------------------------------------------------
@app.route("/schema")
def schema_view():
    """
    Live Database Schema Inspector displaying:
    - Tables & columns
    - Primary & Foreign Key relationships
    - Triggers, Views & Stored Procedures
    """
    tables = [
        "BRANCH", "CUSTOMER", "EMPLOYEE", "ACCOUNT",
        "ACCOUNT_HOLDER", "TRANSACTION", "LOAN", "LOAN_PAYMENT"
    ]
    table_details = {}
    for tbl in tables:
        cols = query_db(f"DESCRIBE {tbl};")
        row_count = query_db(f"SELECT COUNT(*) AS c FROM {tbl};", one=True)['c']
        table_details[tbl] = {
            "columns": cols,
            "count": row_count
        }

    views = query_db("SHOW FULL TABLES WHERE Table_Type = 'VIEW';")
    view_names = [list(v.values())[0] for v in views]

    procedures = query_db("SHOW PROCEDURE STATUS WHERE Db = %s;", (Config.DB_NAME,))
    triggers = query_db("SHOW TRIGGERS FROM project_kashi;")

    return render_template(
        "db_schema.html",
        table_details=table_details,
        view_names=view_names,
        procedures=procedures,
        triggers=triggers,
        active_page="schema"
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
