-- ====================================================================
-- PROJECT KASHI: 10 Meaningful Banking Business Problems & SQL Solutions
-- DBMS Course Project - B.Tech CSE (3rd Semester)
-- Demonstrating: Joins, Aggregation, Subqueries, HAVING, Views, Functions
-- ====================================================================

USE project_kashi;

-- --------------------------------------------------------------------
-- PROBLEM 1: High Net-Worth Customer Identification
-- Business Question:
-- "Who are the top 5 highest-balance customers across all their bank accounts?"
-- Concepts: JOIN, GROUP BY, SUM(), ORDER BY, LIMIT
-- --------------------------------------------------------------------
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

-- --------------------------------------------------------------------
-- PROBLEM 2: Branch Financial Health & Liability Exposure
-- Business Question:
-- "For each branch, compare total customer deposits against total loan
--  amounts disbursed. Highlight branches where loans exceed deposits."
-- Concepts: Multi-table LEFT JOIN, Aggregation, CASE expression
-- --------------------------------------------------------------------
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

-- --------------------------------------------------------------------
-- PROBLEM 3: Dormant / Inactive Account Detection
-- Business Question:
-- "Identify all active accounts that have had NO transactions in the last
--  90 days or zero recorded transactions, so the bank can send alerts."
-- Concepts: NOT EXISTS / LEFT JOIN, Correlated Subquery, DATE_SUB
-- --------------------------------------------------------------------
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

-- --------------------------------------------------------------------
-- PROBLEM 4: Multi-Product Customers (Savings AND Loan Holders)
-- Business Question:
-- "Find all customers who hold both an active Savings account AND
--  have an active Loan with the bank."
-- Concepts: Subqueries with IN, INTERSECT emulation, Multiple Entity Mapping
-- --------------------------------------------------------------------
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

-- --------------------------------------------------------------------
-- PROBLEM 5: High-Value Financial Transactions Audit
-- Business Question:
-- "List all transactions exceeding ₹20,000 for AML (Anti-Money Laundering)
--  compliance audit, including sender details and branch."
-- Concepts: JOIN, WHERE filter, Date formatting, Sorting
-- --------------------------------------------------------------------
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

-- --------------------------------------------------------------------
-- PROBLEM 6: Branch Staffing vs Business Volume Analysis
-- Business Question:
-- "Calculate the average salary paid per branch, total staff count, and
--  deposit volume managed per employee."
-- Concepts: Aggregation, Mathematical Computed Columns, GROUP BY
-- --------------------------------------------------------------------
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

-- --------------------------------------------------------------------
-- PROBLEM 7: Loan Repayment Performance & Outstanding Recovery
-- Business Question:
-- "Determine the outstanding balance on all active loans by subtracting
--  total repayments made to date from the original loan amount."
-- Concepts: LEFT JOIN, Aggregation, COALESCE, Subtraction
-- --------------------------------------------------------------------
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

-- --------------------------------------------------------------------
-- PROBLEM 8: Customers with Multiple Bank Accounts (Cross-Selling)
-- Business Question:
-- "Identify customers holding more than 1 bank account, their total balance,
--  and the distinct account types they hold."
-- Concepts: GROUP BY, HAVING COUNT() > 1, GROUP_CONCAT
-- --------------------------------------------------------------------
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

-- --------------------------------------------------------------------
-- PROBLEM 9: Monthly Transaction Volume and Inflow vs Outflow
-- Business Question:
-- "Summarize total cash inflows (DEPOSIT + TRANSFER_IN) and outflows
--  (WITHDRAWAL + TRANSFER_OUT) grouped by transaction type."
-- Concepts: GROUP BY, SUM(), COUNT(), Percentage Distribution
-- --------------------------------------------------------------------
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

-- --------------------------------------------------------------------
-- PROBLEM 10: City-wise Customer Demographics & Financial Penetration
-- Business Question:
-- "Analyze customer penetration by city: total registered customers,
--  average age, and cumulative wealth parked in the bank."
-- Concepts: TIMESTAMPDIFF with CURDATE, GROUP BY, Aggregation
-- --------------------------------------------------------------------
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
