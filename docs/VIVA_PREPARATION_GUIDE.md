# PROJECT KASHI: Viva Voce Preparation Guide
## Top 30+ Viva Questions & Answers for 3rd Sem B.Tech CSE (DBMS Lab)
**Target Grade:** 10 / 10 Marks  
**Topic:** Banking Management System (HTML, Flask, MySQL 8.0)

---

## Part 1: High-Level Architecture & Project Questions

### Q1. What is the objective of "Project Kashi"?
**Answer:**  
"Project Kashi is a database-driven Banking Management System designed to understand the practical integration of a 3-tier web architecture (Frontend, Backend, and Database) and demonstrate fundamental DBMS concepts like normalization, primary/foreign keys, referential integrity, stored procedures, triggers, views, and ACID transactions."

### Q2. What is the architecture of your application?
**Answer:**  
"Our application follows a **3-Tier Architecture**:
1. **Presentation Layer (Frontend):** Pure semantic HTML5 and Vanilla CSS without frontend frameworks, using forms, tables, and modal dialogs.
2. **Application Layer (Backend):** Python with Flask, which routes HTTP requests, performs input validation, and issues parameterized SQL queries.
3. **Data Layer (Database):** MySQL 8.0 with InnoDB storage engine, storing tables, enforcing constraints, and executing stored routines and triggers."

### Q3. Why did you use pure HTML and CSS instead of React, Angular, or Vue?
**Answer:**  
"As explicitly required by our syllabus and guidelines, raw HTML was used so that we deeply understand how standard HTML forms, method types (GET/POST), inputs, submit buttons, and tables work natively with HTTP cycles and the backend server without framework abstraction."

---

## Part 2: Database Design, ER Model & Normalization

### Q4. How many tables are in your database? Name them.
**Answer:**  
"There are **8 relational tables**:
1. `BRANCH` (Branch metadata and IFSC)
2. `CUSTOMER` (Customer personal and KYC data)
3. `EMPLOYEE` (Bank staff and salaries)
4. `ACCOUNT` (Bank accounts, types, and balances)
5. `ACCOUNT_HOLDER` (M:N junction table connecting customers to accounts)
6. `TRANSACTION` (Financial audit ledger)
7. `LOAN` (Loan contracts, principal, rate, tenure)
8. `LOAN_PAYMENT` (Repayments credited to loans)"

### Q5. Why did you create an `ACCOUNT_HOLDER` table instead of putting `CustomerID` directly in `ACCOUNT`?
**Answer:**  
"Because the relationship between `CUSTOMER` and `ACCOUNT` is **Many-to-Many (M:N)**:
- One customer can have multiple accounts (e.g. a Saving account and a Salary account).
- One account can have multiple owners (e.g. a Joint account with primary and secondary holders).  
To prevent multi-valued attributes and maintain **1st and 2nd Normal Forms**, we resolved the $M:N$ relationship using `ACCOUNT_HOLDER` with a composite primary key `(CustomerID, AccountID)`."

### Q6. How did you normalize your database? Explain 1NF, 2NF, 3NF, and BCNF.
**Answer:**  
- **1NF (First Normal Form):** Every attribute is atomic (indivisible) with no repeating groups. We separated full names into `FirstName` and `LastName`, and split address into `Address`, `City`, and `State`.
- **2NF (Second Normal Form):** In 1NF and no partial functional dependencies. In `ACCOUNT_HOLDER`, attributes `HolderSince` and `HolderType` depend on the *entire* composite key `(CustomerID, AccountID)`.
- **3NF (Third Normal Form):** In 2NF and no transitive dependencies ($X \to Y \to Z$). Branch details (like `IFSCCode` and `City`) are placed in `BRANCH` rather than repeatedly inside `ACCOUNT`.
- **BCNF (Boyce-Codd Normal Form):** For every functional dependency $X \to Y$, determinant $X$ is a super key. All candidate keys in our 8 tables satisfy BCNF.

### Q7. What are the Primary Keys and Foreign Keys in your project?
**Answer:**  
- **Primary Keys:** `BranchID`, `CustomerID`, `EmployeeID`, `AccountID`, `TransactionID`, `LoanID`, `PaymentID`, and composite `(CustomerID, AccountID)` in `ACCOUNT_HOLDER`.
- **Foreign Keys:**
  - `EMPLOYEE.BranchID` &rarr; `BRANCH.BranchID`
  - `ACCOUNT.BranchID` &rarr; `BRANCH.BranchID`
  - `ACCOUNT_HOLDER.CustomerID` &rarr; `CUSTOMER.CustomerID`
  - `ACCOUNT_HOLDER.AccountID` &rarr; `ACCOUNT.AccountID`
  - `TRANSACTION.AccountID` &rarr; `ACCOUNT.AccountID`
  - `LOAN.CustomerID` &rarr; `CUSTOMER.CustomerID`
  - `LOAN.BranchID` &rarr; `BRANCH.BranchID`
  - `LOAN_PAYMENT.LoanID` &rarr; `LOAN.LoanID`

---

## Part 3: Constraints & Data Integrity

### Q8. What constraints did you implement in MySQL?
**Answer:**  
1. **`PRIMARY KEY`** (Entity integrity, unique, non-null)
2. **`FOREIGN KEY ... REFERENCES`** (Referential integrity with `CASCADE` or `RESTRICT`)
3. **`UNIQUE`** on `IFSCCode`, `Mobile`, `Email`, `AccountNumber`, and `ReferenceNumber`
4. **`NOT NULL`** on mandatory fields (names, dates, amounts)
5. **`CHECK` constraints:**
   - `Balance >= 0.00` in `ACCOUNT` (prevents overdraft at DB level)
   - `Amount > 0.00` in `TRANSACTION` and `LOAN_PAYMENT`
   - `Salary > 0.00` in `EMPLOYEE`
6. **`ENUM` domain constraints** for `AccountType`, `Status`, `TransactionType`, and `LoanStatus`.

### Q9. What is the difference between `ON DELETE CASCADE` and `ON DELETE RESTRICT`?
**Answer:**  
- **`ON DELETE CASCADE`:** If a parent row is deleted, MySQL automatically deletes corresponding child rows. We used this on `ACCOUNT_HOLDER` when a customer or account is deleted.
- **`ON DELETE RESTRICT`:** If a child row references a parent row, MySQL blocks deletion of the parent row with a foreign key error. We used this on `BRANCH` and `ACCOUNT` so an active branch with open accounts cannot be accidentally deleted.

---

## Part 4: Transactions & ACID Properties

### Q10. How does your system handle Fund Transfer? Which DBMS concept does it demonstrate?
**Answer:**  
"Fund transfer demonstrates **ACID Transactions** using MySQL Stored Procedure `sp_transfer_funds`:
1. It initiates `START TRANSACTION;`.
2. It locks both sender and receiver account records with `SELECT ... FOR UPDATE` (pessimistic concurrency control).
3. It checks if the sender has sufficient balance and both accounts are `Active`.
4. If valid, it subtracts amount from sender and adds amount to receiver.
5. It inserts two paired audit rows in `TRANSACTION` (`TRANSFER_OUT` and `TRANSFER_IN`).
6. It runs `COMMIT;`. If any step fails or insufficient balance is encountered, it executes `ROLLBACK;` so no money is created or lost."

### Q11. Explain how ACID properties are maintained during a transfer.
**Answer:**  
- **Atomicity:** All-or-nothing execution. Either both debit and credit occur, or neither does (via `COMMIT` and `ROLLBACK`).
- **Consistency:** Total money before the transfer equals total money after the transfer. Check constraint `Balance >= 0` ensures balance never goes negative.
- **Isolation:** Using row locks (`FOR UPDATE`) and InnoDB transaction isolation, concurrent transfers on the same account do not corrupt balances (prevents lost updates).
- **Durability:** Once committed, the changes are written to MySQL's Redo Log and persist even if the server crashes.

---

## Part 5: Stored Procedures, Functions, Triggers, and Views

### Q12. What is the difference between a Stored Procedure and a Stored Function?
**Answer:**  
| Feature | Stored Procedure | Stored Function |
| :--- | :--- | :--- |
| **Return Value** | Can return 0, 1, or multiple values via `OUT` parameters or result sets. | Must return exactly one deterministic scalar value via `RETURNS`. |
| **Invocation** | Executed using `CALL procedure_name(...)`. | Called directly inside SQL statements (e.g. `SELECT fn(...)`). |
| **Modifications** | Can perform INSERT, UPDATE, DELETE, and manage transactions (`START TRANSACTION`, `COMMIT`). | Primarily used for calculations; cannot perform transaction management in standard queries. |
| **Example in Kashi** | `sp_transfer_funds`, `sp_deposit_money`, `sp_withdraw_money` | `fn_customer_total_balance(cust_id)`, `fn_calculate_emi(P, r, N)` |

### Q13. What is a Database Trigger? What triggers exist in Project Kashi?
**Answer:**  
"A trigger is a set of SQL statements that automatically execute in response to a database event (`INSERT`, `UPDATE`, or `DELETE`) on a specified table.  
In our project:
1. **`trg_prevent_negative_balance`** (`BEFORE UPDATE ON ACCOUNT`): If someone attempts to update `Balance < 0.00`, it raises `SIGNAL SQLSTATE '45000'` with message *'Account balance cannot drop below zero'*.
2. **`trg_check_loan_completion`** (`AFTER INSERT ON LOAN_PAYMENT`): When a loan installment is inserted, it computes total repayments to date; if total repayments meet or exceed the original loan amount, it automatically updates `LoanStatus = 'Closed'`."

### Q14. What is a View? Why did you use Views in your project?
**Answer:**  
"A View is a virtual table defined by a SQL query. It does not store physical data; instead, it provides a clean, pre-computed abstraction over complex multi-table joins:
1. **`vw_customer_accounts`:** Joins `CUSTOMER`, `ACCOUNT_HOLDER`, `ACCOUNT`, and `BRANCH` to present customer profiles and their balances in a single clean query.
2. **`vw_passbook`:** Joins `TRANSACTION`, `ACCOUNT`, `BRANCH`, and `CUSTOMER` to render the transaction ledger with formatted names and branches.
3. **`vw_branch_summary`:** Pre-aggregates branch liquidity, account counts, employee counts, and loan exposure for executive reporting."

---

## Part 6: SQL Queries & Business Analytics

### Q15. Can you explain one of the 10 business problem queries from your project?
**Answer:** (Pick Problem 1 or Problem 2)  
*"In Problem 1, we identify the top 5 highest-balance customers:*
```sql
SELECT c.CustomerID, CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName,
       COUNT(a.AccountID) AS TotalAccountsOwned,
       COALESCE(SUM(a.Balance), 0.00) AS TotalAggregateBalance
FROM CUSTOMER c
JOIN ACCOUNT_HOLDER ah ON c.CustomerID = ah.CustomerID
JOIN ACCOUNT a ON ah.AccountID = a.AccountID
WHERE a.Status = 'Active'
GROUP BY c.CustomerID, c.FirstName, c.LastName
ORDER BY TotalAggregateBalance DESC
LIMIT 5;
```
*We use `JOIN` to bridge Customer and Account through `ACCOUNT_HOLDER`, `WHERE` to include only active accounts, `GROUP BY` to aggregate by customer, `SUM()` to calculate total balance, `ORDER BY ... DESC` to rank from richest to lowest, and `LIMIT 5` to select the top 5."*

### Q16. What is the difference between `WHERE` and `HAVING`?
**Answer:**  
- **`WHERE`** filters rows *before* grouping and aggregation take place (e.g. `WHERE a.Status = 'Active'`). It cannot filter aggregate functions directly.
- **`HAVING`** filters aggregated groups *after* `GROUP BY` has executed (e.g. in Problem 3: `HAVING LastTransactionDate IS NULL OR LastTransactionDate < DATE_SUB(NOW(), INTERVAL 90 DAY)`).

### Q17. What is `COALESCE()` and why did you use it?
**Answer:**  
"`COALESCE(expr1, expr2, ...)` returns the first non-null expression. If a customer or branch has no accounts or transactions, `SUM()` returns `NULL`. We wrap aggregates with `COALESCE(SUM(Balance), 0.00)` so it returns `0.00` instead of `NULL`, preventing errors in Python calculations and UI formatting."

---

## Part 7: Practical Demonstration Checklist (During Viva)

When the examiner asks you to demonstrate the project:
1. **Open the Dashboard (`http://127.0.0.1:5000`):**
   - Show the KPI cards (Total Deposits, Disbursed Loans, Customers, Branches).
   - Point out that data is fetched live from MySQL using `vw_branch_summary`.
2. **Go to Operations (`/transactions`):**
   - Click the **Fund Transfer** tab.
   - Choose Account 1 (Rohan Gupta) and Account 2 (Priya Singh).
   - Enter ₹1,000 and click **Execute Transfer**.
   - Show the green confirmation banner: *"Atomic Transfer executed successfully! (ACID Commit applied)"*.
   - Show that Rohan's balance decreased by ₹1,000, Priya's balance increased by ₹1,000, and two matching records (`TRANSFER_OUT` and `TRANSFER_IN`) appeared in the passbook!
3. **Go to SQL 10 Problems (`/analytics`):**
   - Click on **Problem 1**, **Problem 2**, or **Problem 3**.
   - Explain the business question, highlight the DBMS concept tags (e.g. `HAVING`, `LEFT JOIN`, `SUBQUERY`), and show the live query execution table below.
4. **Go to Schema Inspector (`/schema`):**
   - Show the interactive **Mermaid ER Diagram**.
   - Show the 8 table structures, primary/foreign keys, stored procedures, and triggers.
