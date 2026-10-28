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

        # Execute transfer using ACID Transaction with row locks
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                # Check sender balance with row lock
                cursor.execute("SELECT Balance, Status FROM ACCOUNT WHERE AccountID = %s FOR UPDATE;", (sender_id,))
                sender_acc = cursor.fetchone()
                cursor.execute("SELECT Status FROM ACCOUNT WHERE AccountID = %s FOR UPDATE;", (receiver_id,))
                receiver_acc = cursor.fetchone()

                if not sender_acc or not receiver_acc:
                    flash("One or both accounts not found.", "danger")
                    conn.rollback()
                    return redirect(url_for("transfer"))

                if sender_acc.get('Status') != 'Active' or receiver_acc.get('Status') != 'Active':
                    flash("Both accounts must be Active to complete transfer.", "danger")
                    conn.rollback()
                    return redirect(url_for("transfer"))

                if float(sender_acc.get('Balance', 0)) < amount:
                    flash("Insufficient balance in sender account.", "danger")
                    conn.rollback()
                    return redirect(url_for("transfer"))

                # Debit sender and credit receiver
                cursor.execute("UPDATE ACCOUNT SET Balance = Balance - %s WHERE AccountID = %s;", (amount, sender_id))
                cursor.execute("UPDATE ACCOUNT SET Balance = Balance + %s WHERE AccountID = %s;", (amount, receiver_id))

                ref_out = get_ref_number("TXN-OUT")
                ref_in = get_ref_number("TXN-IN")

                cursor.execute("""
                    INSERT INTO `TRANSACTION` (AccountID, TransactionType, Amount, Description, ReferenceNumber, TransactionStatus)
                    VALUES (%s, 'TRANSFER_OUT', %s, %s, %s, 'Success');
                """, (sender_id, amount, desc, ref_out))

                cursor.execute("""
                    INSERT INTO `TRANSACTION` (AccountID, TransactionType, Amount, Description, ReferenceNumber, TransactionStatus)
                    VALUES (%s, 'TRANSFER_IN', %s, %s, %s, 'Success');
                """, (receiver_id, amount, desc, ref_in))

                conn.commit()
                flash(f"Transfer of ₹{amount:,.2f} completed successfully! (ACID Transaction Committed)", "success")
                return redirect(url_for("passbook"))
        except Exception as e:
            conn.rollback()
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

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
