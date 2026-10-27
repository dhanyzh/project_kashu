import os
import sys
import random
import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash

# Ensure parent directory is in path
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

# Helper function to generate unique account number
def get_new_account_number():
    return f"100100{random.randint(1000, 9999)}"

# Helper function to generate reference number
def get_ref_number(prefix="TXN"):
    return f"{prefix}-{int(time.time())}-{random.randint(100, 999)}"

# --------------------------------------------------------------------
# 1. HOME / DASHBOARD
# --------------------------------------------------------------------
@app.route("/")
def home():
    total_customers = query_db("SELECT COUNT(*) AS c FROM CUSTOMER;", one=True)['c']
    total_accounts = query_db("SELECT COUNT(*) AS c FROM ACCOUNT WHERE Status = 'Active';", one=True)['c']
    total_balance = query_db("SELECT COALESCE(SUM(Balance), 0) AS total FROM ACCOUNT WHERE Status = 'Active';", one=True)['total']
    total_txns = query_db("SELECT COUNT(*) AS c FROM TRANSACTION;", one=True)['c']
    total_loans = query_db("SELECT COUNT(*) AS c FROM LOAN;", one=True)['c']
    
    # 5 recent transactions
    recent_txns = query_db("""
        SELECT t.TransactionDate, t.ReferenceNumber, a.AccountNumber, 
               t.TransactionType, t.Amount, t.Description
        FROM TRANSACTION t
        JOIN ACCOUNT a ON t.AccountID = a.AccountID
        ORDER BY t.TransactionDate DESC LIMIT 5;
    """)

    return render_template(
        "index.html",
        total_customers=total_customers,
        total_accounts=total_accounts,
        total_balance=total_balance,
        total_txns=total_txns,
        total_loans=total_loans,
        recent_txns=recent_txns,
        active_page="home"
    )

# --------------------------------------------------------------------
# 2. OPEN NEW ACCOUNT (Register Customer + Create Account)
# --------------------------------------------------------------------
@app.route("/open-account", methods=["GET", "POST"])
def open_account():
    branches = query_db("SELECT BranchID, BranchName, IFSCCode, City FROM BRANCH ORDER BY BranchName;")
    existing_customers = query_db("SELECT CustomerID, CONCAT(FirstName, ' ', LastName) AS Name, Mobile FROM CUSTOMER ORDER BY FirstName;")

    if request.method == "POST":
        conn = get_connection()
        try:
            user_type = request.form.get("user_type", "new")
            branch_id = int(request.form.get("branch_id"))
            account_type = request.form.get("account_type", "Saving")
            initial_deposit = float(request.form.get("initial_deposit", 0.0) or 0.0)
            today = datetime.now().strftime("%Y-%m-%d")

            with conn.cursor() as cursor:
                # If creating for a new customer
                if user_type == "new":
                    first_name = request.form.get("first_name", "").strip()
                    last_name = request.form.get("last_name", "").strip()
                    dob = request.form.get("dob")
                    gender = request.form.get("gender")
                    mobile = request.form.get("mobile", "").strip()
                    email = request.form.get("email", "").strip()
                    address = request.form.get("address", "").strip()
                    city = request.form.get("city", "").strip()

                    # Insert Customer
                    cursor.execute("""
                        INSERT INTO CUSTOMER (FirstName, LastName, DateOfBirth, Gender, Mobile, Email, Address, City)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """, (first_name, last_name, dob, gender, mobile, email, address, city))
                    customer_id = cursor.lastrowid
                else:
                    customer_id = int(request.form.get("existing_customer_id"))

                # Generate Account Number
                acc_num = get_new_account_number()

                # Insert Account
                cursor.execute("""
                    INSERT INTO ACCOUNT (AccountNumber, AccountType, OpeningDate, Balance, Status, BranchID)
                    VALUES (%s, %s, %s, %s, 'Active', %s);
                """, (acc_num, account_type, today, initial_deposit, branch_id))
                account_id = cursor.lastrowid

                # Link Customer and Account in ACCOUNT_HOLDER
                cursor.execute("""
                    INSERT INTO ACCOUNT_HOLDER (CustomerID, AccountID, HolderSince, HolderType)
                    VALUES (%s, %s, %s, 'Primary');
                """, (customer_id, account_id, today))

                # If initial deposit > 0, record in TRANSACTION table
                if initial_deposit > 0:
                    ref = get_ref_number("TXN-DEP")
                    cursor.execute("""
                        INSERT INTO TRANSACTION (AccountID, TransactionType, Amount, Description, ReferenceNumber, TransactionStatus)
                        VALUES (%s, 'DEPOSIT', %s, 'Opening Initial Deposit', %s, 'SUCCESS');
                    """, (account_id, initial_deposit, ref))

                conn.commit()
                flash(f"Success! Account #{acc_num} opened with initial balance of ₹{initial_deposit:,.2f}!", "success")
                return redirect(url_for("customers"))
        except Exception as e:
            conn.rollback()
            flash(f"Error opening account: {str(e)}", "danger")
        finally:
            conn.close()

    return render_template("open_account.html", branches=branches, existing_customers=existing_customers, active_page="open_account")

# --------------------------------------------------------------------
# 3. DEPOSIT MONEY
# --------------------------------------------------------------------
@app.route("/deposit", methods=["GET", "POST"])
def deposit():
    accounts = query_db("""
        SELECT a.AccountID, a.AccountNumber, a.Balance, a.AccountType, 
               CONCAT(c.FirstName, ' ', c.LastName) AS OwnerName
        FROM ACCOUNT a
        JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID AND ah.HolderType = 'Primary'
        JOIN CUSTOMER c ON ah.CustomerID = c.CustomerID
        WHERE a.Status = 'Active'
        ORDER BY a.AccountNumber;
    """)

    if request.method == "POST":
        try:
            account_id = int(request.form.get("account_id"))
            amount = float(request.form.get("amount", 0))
            desc = request.form.get("description", "Cash Deposit")

            if amount <= 0:
                flash("Deposit amount must be greater than zero.", "danger")
                return redirect(url_for("deposit"))

            # Update balance and log transaction
            conn = get_connection()
            with conn.cursor() as cursor:
                cursor.execute("UPDATE ACCOUNT SET Balance = Balance + %s WHERE AccountID = %s;", (amount, account_id))
                ref = get_ref_number("TXN-DEP")
                cursor.execute("""
                    INSERT INTO TRANSACTION (AccountID, TransactionType, Amount, Description, ReferenceNumber, TransactionStatus)
                    VALUES (%s, 'DEPOSIT', %s, %s, %s, 'SUCCESS');
                """, (account_id, amount, desc, ref))
                conn.commit()
            conn.close()

            flash(f"₹{amount:,.2f} deposited successfully! Ref No: {ref}", "success")
            return redirect(url_for("passbook"))
        except Exception as e:
            flash(f"Deposit failed: {str(e)}", "danger")

    return render_template("deposit.html", accounts=accounts, active_page="deposit")

# --------------------------------------------------------------------
# 4. WITHDRAW MONEY
# --------------------------------------------------------------------
@app.route("/withdraw", methods=["GET", "POST"])
def withdraw():
    accounts = query_db("""
        SELECT a.AccountID, a.AccountNumber, a.Balance, a.AccountType, 
               CONCAT(c.FirstName, ' ', c.LastName) AS OwnerName
        FROM ACCOUNT a
        JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID AND ah.HolderType = 'Primary'
        JOIN CUSTOMER c ON ah.CustomerID = c.CustomerID
        WHERE a.Status = 'Active'
        ORDER BY a.AccountNumber;
    """)

    if request.method == "POST":
        try:
            account_id = int(request.form.get("account_id"))
            amount = float(request.form.get("amount", 0))
            desc = request.form.get("description", "Cash Withdrawal")

            if amount <= 0:
                flash("Withdrawal amount must be greater than zero.", "danger")
                return redirect(url_for("withdraw"))

            conn = get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT Balance FROM ACCOUNT WHERE AccountID = %s;", (account_id,))
                row = cursor.fetchone()
                if not row or row['Balance'] < amount:
                    flash(f"Withdrawal failed: Insufficient balance. Available: ₹{row['Balance'] if row else 0:,.2f}", "danger")
                    conn.close()
                    return redirect(url_for("withdraw"))

                cursor.execute("UPDATE ACCOUNT SET Balance = Balance - %s WHERE AccountID = %s;", (amount, account_id))
                ref = get_ref_number("TXN-WTH")
                cursor.execute("""
                    INSERT INTO TRANSACTION (AccountID, TransactionType, Amount, Description, ReferenceNumber, TransactionStatus)
                    VALUES (%s, 'WITHDRAWAL', %s, %s, %s, 'SUCCESS');
                """, (account_id, amount, desc, ref))
                conn.commit()
            conn.close()

            flash(f"₹{amount:,.2f} withdrawn successfully! Ref No: {ref}", "success")
            return redirect(url_for("passbook"))
        except Exception as e:
            flash(f"Withdrawal failed: {str(e)}", "danger")

    return render_template("withdraw.html", accounts=accounts, active_page="withdraw")

# --------------------------------------------------------------------
# 5. TRANSFER FUNDS (Atomic Transfer)
# --------------------------------------------------------------------
@app.route("/transfer", methods=["GET", "POST"])
def transfer():
    accounts = query_db("""
        SELECT a.AccountID, a.AccountNumber, a.Balance, a.AccountType, 
               CONCAT(c.FirstName, ' ', c.LastName) AS OwnerName
        FROM ACCOUNT a
        JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID AND ah.HolderType = 'Primary'
        JOIN CUSTOMER c ON ah.CustomerID = c.CustomerID
        WHERE a.Status = 'Active'
        ORDER BY a.AccountNumber;
    """)

    if request.method == "POST":
        sender_id = int(request.form.get("sender_id"))
        receiver_id = int(request.form.get("receiver_id"))
        amount = float(request.form.get("amount", 0))
        desc = request.form.get("description", "Fund Transfer")

        if sender_id == receiver_id:
            flash("Sender and Receiver cannot be the same account.", "danger")
            return redirect(url_for("transfer"))

        if amount <= 0:
            flash("Transfer amount must be greater than zero.", "danger")
            return redirect(url_for("transfer"))

        # Execute using Stored Procedure sp_transfer_funds (Atomic ACID Transaction)
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("CALL sp_transfer_funds(%s, %s, %s, %s, @status_code, @status_msg);",
                               (sender_id, receiver_id, amount, desc))
                cursor.execute("SELECT @status_code AS code, @status_msg AS msg;")
                res = cursor.fetchone()

                if res and res['code'] == 200:
                    flash(f"Transfer of ₹{amount:,.2f} completed successfully! (ACID Transaction Committed)", "success")
                    return redirect(url_for("passbook"))
                else:
                    flash(f"Transfer failed: {res['msg'] if res else 'Unknown error'}", "danger")
        except Exception as e:
            flash(f"Error during transfer: {str(e)}", "danger")
        finally:
            conn.close()

    return render_template("transfer.html", accounts=accounts, active_page="transfer")

# --------------------------------------------------------------------
# 6. PASSBOOK / TRANSACTION HISTORY
# --------------------------------------------------------------------
@app.route("/passbook")
def passbook():
    filter_acc = request.args.get("account_number", "").strip()
    
    if filter_acc:
        txns = query_db("""
            SELECT t.TransactionID, t.TransactionDate, t.ReferenceNumber, a.AccountNumber,
                   t.TransactionType, t.Amount, t.Description, t.TransactionStatus,
                   CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName
            FROM TRANSACTION t
            JOIN ACCOUNT a ON t.AccountID = a.AccountID
            JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID AND ah.HolderType = 'Primary'
            JOIN CUSTOMER c ON ah.CustomerID = c.CustomerID
            WHERE a.AccountNumber = %s
            ORDER BY t.TransactionDate DESC;
        """, (filter_acc,))
    else:
        txns = query_db("""
            SELECT t.TransactionID, t.TransactionDate, t.ReferenceNumber, a.AccountNumber,
                   t.TransactionType, t.Amount, t.Description, t.TransactionStatus,
                   CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName
            FROM TRANSACTION t
            JOIN ACCOUNT a ON t.AccountID = a.AccountID
            JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID AND ah.HolderType = 'Primary'
            JOIN CUSTOMER c ON ah.CustomerID = c.CustomerID
            ORDER BY t.TransactionDate DESC;
        """)

    return render_template("passbook.html", txns=txns, filter_acc=filter_acc, active_page="passbook")

# --------------------------------------------------------------------
# 7. CUSTOMERS & ACCOUNTS LIST
# --------------------------------------------------------------------
@app.route("/customers")
def customers():
    customer_list = query_db("""
        SELECT c.CustomerID, CONCAT(c.FirstName, ' ', c.LastName) AS FullName,
               c.Mobile, c.Email, c.City,
               a.AccountNumber, a.AccountType, a.Balance, a.Status, b.BranchName
        FROM CUSTOMER c
        LEFT JOIN ACCOUNT_HOLDER ah ON c.CustomerID = ah.CustomerID
        LEFT JOIN ACCOUNT a ON ah.AccountID = a.AccountID
        LEFT JOIN BRANCH b ON a.BranchID = b.BranchID
        ORDER BY c.CustomerID DESC;
    """)
    return render_template("customers.html", customers=customer_list, active_page="customers")

# --------------------------------------------------------------------
# 8. LOANS (Apply & Pay)
# --------------------------------------------------------------------
@app.route("/loans", methods=["GET", "POST"])
def loans():
    branches = query_db("SELECT BranchID, BranchName FROM BRANCH ORDER BY BranchName;")
    custs = query_db("SELECT CustomerID, CONCAT(FirstName, ' ', LastName) AS Name FROM CUSTOMER ORDER BY FirstName;")
    
    if request.method == "POST":
        action = request.form.get("action")
        
        # 1. Apply Loan
        if action == "apply":
            try:
                cust_id = int(request.form.get("customer_id"))
                branch_id = int(request.form.get("branch_id"))
                loan_type = request.form.get("loan_type")
                amount = float(request.form.get("amount"))
                rate = float(request.form.get("rate", 8.5))
                tenure = int(request.form.get("tenure", 36))
                today = datetime.now().strftime("%Y-%m-%d")

                execute_db("""
                    INSERT INTO LOAN (CustomerID, BranchID, LoanType, LoanAmount, InterestRate, StartDate, TenureMonths, LoanStatus)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'Disbursed');
                """, (cust_id, branch_id, loan_type, amount, rate, today, tenure))

                flash(f"Loan of ₹{amount:,.2f} applied and disbursed successfully!", "success")
            except Exception as e:
                flash(f"Failed to apply loan: {str(e)}", "danger")

        # 2. Pay Loan
        elif action == "pay":
            try:
                loan_id = int(request.form.get("loan_id"))
                pay_amount = float(request.form.get("amount"))
                mode = request.form.get("payment_mode", "NetBanking")
                ref = get_ref_number("LPAY")

                execute_db("""
                    INSERT INTO LOAN_PAYMENT (LoanID, Amount, PaymentMode, ReferenceNumber)
                    VALUES (%s, %s, %s, %s);
                """, (loan_id, pay_amount, mode, ref))

                flash(f"Payment of ₹{pay_amount:,.2f} recorded! (Trigger auto-checked loan completion)", "success")
            except Exception as e:
                flash(f"Failed to record loan payment: {str(e)}", "danger")

        return redirect(url_for("loans"))

    # Fetch loans with total paid
    loan_list = query_db("""
        SELECT l.LoanID, CONCAT(c.FirstName, ' ', c.LastName) AS BorrowerName,
               l.LoanType, l.LoanAmount, l.InterestRate, l.TenureMonths, l.LoanStatus,
               b.BranchName,
               COALESCE(SUM(lp.Amount), 0) AS TotalPaid,
               (l.LoanAmount - COALESCE(SUM(lp.Amount), 0)) AS Outstanding
        FROM LOAN l
        JOIN CUSTOMER c ON l.CustomerID = c.CustomerID
        JOIN BRANCH b ON l.BranchID = b.BranchID
        LEFT JOIN LOAN_PAYMENT lp ON l.LoanID = lp.LoanID
        GROUP BY l.LoanID
        ORDER BY l.LoanID DESC;
    """)

    return render_template("loans.html", loans=loan_list, branches=branches, customers=custs, active_page="loans")

# --------------------------------------------------------------------
# 9. 10 SQL BUSINESS PROBLEMS
# --------------------------------------------------------------------
@app.route("/queries")
def queries():
    selected = int(request.args.get("id", 1))

    queries_dict = {
        1: {
            "title": "Problem 1: Top 5 Highest Balance Customers",
            "question": "Find the top 5 customers with the highest total balance across all accounts.",
            "sql": "SELECT c.CustomerID, CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName, c.Mobile, c.City, SUM(a.Balance) AS TotalBalance FROM CUSTOMER c JOIN ACCOUNT_HOLDER ah ON c.CustomerID = ah.CustomerID JOIN ACCOUNT a ON ah.AccountID = a.AccountID WHERE a.Status = 'Active' GROUP BY c.CustomerID, c.FirstName, c.LastName, c.Mobile, c.City ORDER BY TotalBalance DESC LIMIT 5;"
        },
        2: {
            "title": "Problem 2: Branch Deposits vs Loans",
            "question": "Compare total deposits against total loans disbursed per branch.",
            "sql": "SELECT b.BranchName, b.City, COALESCE(SUM(a.Balance), 0) AS TotalDeposits, COALESCE(l.TotalLoans, 0) AS TotalLoans FROM BRANCH b LEFT JOIN ACCOUNT a ON b.BranchID = a.BranchID LEFT JOIN (SELECT BranchID, SUM(LoanAmount) AS TotalLoans FROM LOAN GROUP BY BranchID) l ON b.BranchID = l.BranchID GROUP BY b.BranchID, b.BranchName, b.City, l.TotalLoans;"
        },
        3: {
            "title": "Problem 3: Inactive Accounts (No Transactions)",
            "question": "Find active accounts with zero transactions in the last 90 days.",
            "sql": "SELECT a.AccountID, a.AccountNumber, a.AccountType, a.Balance, CONCAT(c.FirstName, ' ', c.LastName) AS OwnerName, MAX(t.TransactionDate) AS LastTxnDate FROM ACCOUNT a JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID JOIN CUSTOMER c ON ah.CustomerID = c.CustomerID LEFT JOIN TRANSACTION t ON a.AccountID = t.AccountID WHERE a.Status = 'Active' GROUP BY a.AccountID, a.AccountNumber, a.AccountType, a.Balance, c.FirstName, c.LastName HAVING LastTxnDate IS NULL OR LastTxnDate < DATE_SUB(NOW(), INTERVAL 90 DAY);"
        },
        4: {
            "title": "Problem 4: Customers Having Both Savings Account and Loan",
            "question": "Find all customers who have a Savings account AND a loan with the bank.",
            "sql": "SELECT DISTINCT c.CustomerID, CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName, c.Mobile, l.LoanType, l.LoanAmount FROM CUSTOMER c JOIN LOAN l ON c.CustomerID = l.CustomerID WHERE c.CustomerID IN (SELECT ah.CustomerID FROM ACCOUNT_HOLDER ah JOIN ACCOUNT a ON ah.AccountID = a.AccountID WHERE a.AccountType = 'Saving');"
        },
        5: {
            "title": "Problem 5: High-Value Transactions (Above ₹20,000)",
            "question": "List all transactions of ₹20,000 or more for bank auditing.",
            "sql": "SELECT t.TransactionID, t.ReferenceNumber, t.TransactionDate, t.TransactionType, t.Amount, a.AccountNumber, CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName FROM TRANSACTION t JOIN ACCOUNT a ON t.AccountID = a.AccountID JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID JOIN CUSTOMER c ON ah.CustomerID = c.CustomerID WHERE t.Amount >= 20000 ORDER BY t.Amount DESC;"
        },
        6: {
            "title": "Problem 6: Branch Staff and Average Salary",
            "question": "Calculate total staff and average employee salary per branch.",
            "sql": "SELECT b.BranchName, COUNT(e.EmployeeID) AS TotalEmployees, ROUND(AVG(e.Salary), 2) AS AverageSalary FROM BRANCH b LEFT JOIN EMPLOYEE e ON b.BranchID = e.BranchID GROUP BY b.BranchID, b.BranchName;"
        },
        7: {
            "title": "Problem 7: Loan Repayment Tracking",
            "question": "Calculate total amount repaid and remaining balance for each loan.",
            "sql": "SELECT l.LoanID, CONCAT(c.FirstName, ' ', c.LastName) AS Borrower, l.LoanType, l.LoanAmount, COALESCE(SUM(lp.Amount), 0) AS TotalPaid, (l.LoanAmount - COALESCE(SUM(lp.Amount), 0)) AS RemainingAmount, l.LoanStatus FROM LOAN l JOIN CUSTOMER c ON l.CustomerID = c.CustomerID LEFT JOIN LOAN_PAYMENT lp ON l.LoanID = lp.LoanID GROUP BY l.LoanID, c.FirstName, c.LastName, l.LoanType, l.LoanAmount, l.LoanStatus;"
        },
        8: {
            "title": "Problem 8: Customers with Multiple Bank Accounts",
            "question": "Identify customers holding more than 1 account in the bank.",
            "sql": "SELECT c.CustomerID, CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName, COUNT(ah.AccountID) AS TotalAccounts, SUM(a.Balance) AS CombinedBalance FROM CUSTOMER c JOIN ACCOUNT_HOLDER ah ON c.CustomerID = ah.CustomerID JOIN ACCOUNT a ON ah.AccountID = a.AccountID GROUP BY c.CustomerID, c.FirstName, c.LastName HAVING COUNT(ah.AccountID) > 1;"
        },
        9: {
            "title": "Problem 9: Total Money Moved by Transaction Type",
            "question": "Calculate total transaction count and sum of money by transaction type.",
            "sql": "SELECT TransactionType, COUNT(*) AS TotalCount, SUM(Amount) AS TotalAmount, ROUND(AVG(Amount), 2) AS AverageAmount FROM TRANSACTION GROUP BY TransactionType ORDER BY TotalAmount DESC;"
        },
        10: {
            "title": "Problem 10: Customers and Deposits by City",
            "question": "Show count of registered customers and total money deposited per city.",
            "sql": "SELECT c.City, COUNT(DISTINCT c.CustomerID) AS CustomerCount, COALESCE(SUM(a.Balance), 0) AS TotalCityDeposits FROM CUSTOMER c LEFT JOIN ACCOUNT_HOLDER ah ON c.CustomerID = ah.CustomerID LEFT JOIN ACCOUNT a ON ah.AccountID = a.AccountID GROUP BY c.City ORDER BY TotalCityDeposits DESC;"
        }
    }

    current = queries_dict.get(selected, queries_dict[1])
    try:
        results = query_db(current["sql"])
        columns = list(results[0].keys()) if results else []
    except Exception as e:
        results = []
        columns = []
        flash(f"SQL Error: {str(e)}", "danger")

    return render_template(
        "queries.html",
        queries=queries_dict,
        selected=selected,
        current=current,
        columns=columns,
        results=results,
        active_page="queries"
    )

# --------------------------------------------------------------------
# 10. DATABASE SCHEMA & ER DIAGRAM
# --------------------------------------------------------------------
@app.route("/database")
def database():
    return render_template("database.html", active_page="database")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
