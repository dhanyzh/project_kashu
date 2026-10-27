-- Shreehari Finance: 10 SQL Business Queries
-- Course: Database Management Systems Lab (3rd Sem B.Tech CSE)
-- Database: project_kashi

USE project_kashi;

-- Query 1: Find top 5 customers with the highest total bank balance
SELECT 
    c.CustomerID,
    CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName,
    c.Mobile,
    c.City,
    COUNT(a.AccountID) AS TotalAccounts,
    SUM(a.Balance) AS TotalBalance
FROM CUSTOMER c
JOIN ACCOUNT_HOLDER ah ON c.CustomerID = ah.CustomerID
JOIN ACCOUNT a ON ah.AccountID = a.AccountID
WHERE a.Status = 'Active'
GROUP BY c.CustomerID, c.FirstName, c.LastName, c.Mobile, c.City
ORDER BY TotalBalance DESC
LIMIT 5;

-- Query 2: Compare total customer deposits and total loans given per branch
SELECT 
    b.BranchName,
    b.City,
    COALESCE(SUM(a.Balance), 0) AS TotalDeposits,
    COALESCE(l.TotalLoans, 0) AS TotalLoans
FROM BRANCH b
LEFT JOIN ACCOUNT a ON b.BranchID = a.BranchID
LEFT JOIN (
    SELECT BranchID, SUM(LoanAmount) AS TotalLoans 
    FROM LOAN 
    GROUP BY BranchID
) l ON b.BranchID = l.BranchID
GROUP BY b.BranchID, b.BranchName, b.City, l.TotalLoans
ORDER BY TotalDeposits DESC;

-- Query 3: Find active accounts with no transactions in the last 90 days
SELECT 
    a.AccountID,
    a.AccountNumber,
    a.AccountType,
    a.Balance,
    CONCAT(c.FirstName, ' ', c.LastName) AS OwnerName,
    MAX(t.TransactionDate) AS LastTxnDate
FROM ACCOUNT a
JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID
JOIN CUSTOMER c ON ah.CustomerID = c.CustomerID
LEFT JOIN TRANSACTION t ON a.AccountID = t.AccountID
WHERE a.Status = 'Active'
GROUP BY a.AccountID, a.AccountNumber, a.AccountType, a.Balance, c.FirstName, c.LastName
HAVING LastTxnDate IS NULL OR LastTxnDate < DATE_SUB(NOW(), INTERVAL 90 DAY);

-- Query 4: Find customers who have both a Savings Account and a Loan
SELECT DISTINCT 
    c.CustomerID,
    CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName,
    c.Mobile,
    l.LoanType,
    l.LoanAmount
FROM CUSTOMER c
JOIN LOAN l ON c.CustomerID = l.CustomerID
WHERE c.CustomerID IN (
    SELECT ah.CustomerID
    FROM ACCOUNT_HOLDER ah
    JOIN ACCOUNT a ON ah.AccountID = a.AccountID
    WHERE a.AccountType = 'Saving'
);

-- Query 5: Find all high value transactions (amount >= 20,000) for audit
SELECT 
    t.TransactionID,
    t.ReferenceNumber,
    t.TransactionDate,
    t.TransactionType,
    t.Amount,
    a.AccountNumber,
    CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName
FROM TRANSACTION t
JOIN ACCOUNT a ON t.AccountID = a.AccountID
JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID
JOIN CUSTOMER c ON ah.CustomerID = c.CustomerID
WHERE t.Amount >= 20000
ORDER BY t.Amount DESC;

-- Query 6: Find total employees and average employee salary per branch
SELECT 
    b.BranchName,
    COUNT(e.EmployeeID) AS TotalEmployees,
    ROUND(AVG(e.Salary), 2) AS AverageSalary
FROM BRANCH b
LEFT JOIN EMPLOYEE e ON b.BranchID = e.BranchID
GROUP BY b.BranchID, b.BranchName;

-- Query 7: Track loan repayments and find remaining loan balance
SELECT 
    l.LoanID,
    CONCAT(c.FirstName, ' ', c.LastName) AS Borrower,
    l.LoanType,
    l.LoanAmount AS PrincipalAmount,
    COALESCE(SUM(lp.Amount), 0) AS TotalPaid,
    (l.LoanAmount - COALESCE(SUM(lp.Amount), 0)) AS RemainingAmount,
    l.LoanStatus
FROM LOAN l
JOIN CUSTOMER c ON l.CustomerID = c.CustomerID
LEFT JOIN LOAN_PAYMENT lp ON l.LoanID = lp.LoanID
GROUP BY l.LoanID, c.FirstName, c.LastName, l.LoanType, l.LoanAmount, l.LoanStatus;

-- Query 8: Find customers who hold more than one bank account
SELECT 
    c.CustomerID,
    CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName,
    COUNT(ah.AccountID) AS TotalAccounts,
    SUM(a.Balance) AS CombinedBalance
FROM CUSTOMER c
JOIN ACCOUNT_HOLDER ah ON c.CustomerID = ah.CustomerID
JOIN ACCOUNT a ON ah.AccountID = a.AccountID
GROUP BY c.CustomerID, c.FirstName, c.LastName
HAVING COUNT(ah.AccountID) > 1;

-- Query 9: Calculate total transactions and sum of money by transaction type
SELECT 
    TransactionType,
    COUNT(*) AS TotalCount,
    SUM(Amount) AS TotalAmount,
    ROUND(AVG(Amount), 2) AS AverageAmount
FROM TRANSACTION
GROUP BY TransactionType
ORDER BY TotalAmount DESC;

-- Query 10: Find total customers and deposits grouped by city
SELECT 
    c.City,
    COUNT(DISTINCT c.CustomerID) AS CustomerCount,
    COALESCE(SUM(a.Balance), 0) AS TotalCityDeposits
FROM CUSTOMER c
LEFT JOIN ACCOUNT_HOLDER ah ON c.CustomerID = ah.CustomerID
LEFT JOIN ACCOUNT a ON ah.AccountID = a.AccountID
GROUP BY c.City
ORDER BY TotalCityDeposits DESC;
