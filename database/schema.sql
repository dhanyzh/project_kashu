-- Project Name: Shreehari Finance (Banking Management System)
-- Subject: Database Management Systems Lab (DBMS)
-- Semester: 3rd Sem B.Tech CSE
-- Database: MySQL 8.0

DROP DATABASE IF EXISTS project_kashi;
CREATE DATABASE project_kashi;
USE project_kashi;

-- Branch table (created first because account and employee reference branch id)
CREATE TABLE BRANCH (
    BranchID INT AUTO_INCREMENT PRIMARY KEY,
    BranchName VARCHAR(100) NOT NULL,
    IFSCCode VARCHAR(20) NOT NULL UNIQUE,
    Address VARCHAR(255) NOT NULL,
    City VARCHAR(50) NOT NULL,
    State VARCHAR(50) NOT NULL,
    ContactNumber VARCHAR(15) NOT NULL,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Customer table to store personal details
CREATE TABLE CUSTOMER (
    CustomerID INT AUTO_INCREMENT PRIMARY KEY,
    FirstName VARCHAR(50) NOT NULL,
    LastName VARCHAR(50) NOT NULL,
    DateOfBirth DATE NOT NULL,
    Gender ENUM('Male', 'Female', 'Other') NOT NULL,
    Mobile VARCHAR(15) NOT NULL UNIQUE,
    Email VARCHAR(100) NOT NULL UNIQUE,
    Address VARCHAR(255) NOT NULL,
    City VARCHAR(50) NOT NULL,
    RegistrationDate DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Employee table with branch reference
CREATE TABLE EMPLOYEE (
    EmployeeID INT AUTO_INCREMENT PRIMARY KEY,
    EmployeeName VARCHAR(100) NOT NULL,
    Mobile VARCHAR(15) NOT NULL,
    Email VARCHAR(100) NOT NULL UNIQUE,
    Designation VARCHAR(50) NOT NULL,
    Salary DECIMAL(12, 2) NOT NULL CHECK (Salary > 0),
    JoiningDate DATE NOT NULL,
    BranchID INT NOT NULL,
    FOREIGN KEY (BranchID) REFERENCES BRANCH(BranchID)
);

-- Account table (Saving, Current, Salary accounts)
CREATE TABLE ACCOUNT (
    AccountID INT AUTO_INCREMENT PRIMARY KEY,
    AccountNumber VARCHAR(20) NOT NULL UNIQUE,
    AccountType ENUM('Saving', 'Current', 'Salary') NOT NULL,
    OpeningDate DATE NOT NULL,
    Balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00 CHECK (Balance >= 0.00),
    Status ENUM('Active', 'Inactive', 'Close') NOT NULL DEFAULT 'Active',
    BranchID INT NOT NULL,
    FOREIGN KEY (BranchID) REFERENCES BRANCH(BranchID)
);

-- Junction table for Many-to-Many connection between Customer and Account
CREATE TABLE ACCOUNT_HOLDER (
    CustomerID INT NOT NULL,
    AccountID INT NOT NULL,
    HolderSince DATE NOT NULL,
    HolderType VARCHAR(20) DEFAULT 'Primary',
    PRIMARY KEY (CustomerID, AccountID),
    FOREIGN KEY (CustomerID) REFERENCES CUSTOMER(CustomerID) ON DELETE CASCADE,
    FOREIGN KEY (AccountID) REFERENCES ACCOUNT(AccountID) ON DELETE CASCADE
);

-- Transaction table for deposit, withdrawal, and transfer records
CREATE TABLE TRANSACTION (
    TransactionID INT AUTO_INCREMENT PRIMARY KEY,
    AccountID INT NOT NULL,
    TransactionType ENUM('DEPOSIT', 'WITHDRAWAL', 'TRANSFER_IN', 'TRANSFER_OUT') NOT NULL,
    Amount DECIMAL(15, 2) NOT NULL CHECK (Amount > 0.00),
    TransactionDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    Description VARCHAR(255),
    ReferenceNumber VARCHAR(50) NOT NULL UNIQUE,
    TransactionStatus ENUM('SUCCESS', 'FAILED', 'PENDING') DEFAULT 'SUCCESS',
    FOREIGN KEY (AccountID) REFERENCES ACCOUNT(AccountID)
);

-- Loan table
CREATE TABLE LOAN (
    LoanID INT AUTO_INCREMENT PRIMARY KEY,
    CustomerID INT NOT NULL,
    BranchID INT NOT NULL,
    LoanType ENUM('Home Loan', 'Education Loan', 'Personal Loan', 'Vehicle Loan') NOT NULL,
    LoanAmount DECIMAL(15, 2) NOT NULL CHECK (LoanAmount > 0.00),
    InterestRate DECIMAL(5, 2) NOT NULL CHECK (InterestRate >= 0.00),
    StartDate DATE NOT NULL,
    TenureMonths INT NOT NULL CHECK (TenureMonths > 0),
    LoanStatus ENUM('Applied', 'Approved', 'Disbursed', 'Closed', 'Rejected') DEFAULT 'Approved',
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CustomerID) REFERENCES CUSTOMER(CustomerID),
    FOREIGN KEY (BranchID) REFERENCES BRANCH(BranchID)
);

-- Loan Payment table
CREATE TABLE LOAN_PAYMENT (
    PaymentID INT AUTO_INCREMENT PRIMARY KEY,
    LoanID INT NOT NULL,
    PaymentDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    Amount DECIMAL(15, 2) NOT NULL CHECK (Amount > 0.00),
    PaymentMode VARCHAR(30) NOT NULL,
    ReferenceNumber VARCHAR(50) NOT NULL UNIQUE,
    FOREIGN KEY (LoanID) REFERENCES LOAN(LoanID)
);

-- View 1: Customer and their account details with branch IFSC
CREATE OR REPLACE VIEW vw_customer_accounts AS
SELECT 
    c.CustomerID,
    CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName,
    c.Mobile,
    c.Email,
    c.City AS CustomerCity,
    a.AccountID,
    a.AccountNumber,
    a.AccountType,
    a.Balance,
    a.Status AS AccountStatus,
    ah.HolderType,
    b.BranchName,
    b.IFSCCode
FROM CUSTOMER c
JOIN ACCOUNT_HOLDER ah ON c.CustomerID = ah.CustomerID
JOIN ACCOUNT a ON ah.AccountID = a.AccountID
JOIN BRANCH b ON a.BranchID = b.BranchID;

-- View 2: Passbook view joining transactions with accounts and customer name
CREATE OR REPLACE VIEW vw_passbook AS
SELECT 
    t.TransactionID,
    t.TransactionDate,
    t.ReferenceNumber,
    a.AccountNumber,
    CONCAT(c.FirstName, ' ', c.LastName) AS AccountHolder,
    t.TransactionType,
    t.Amount,
    a.Balance AS CurrentBalance,
    t.Description,
    t.TransactionStatus,
    b.BranchName
FROM TRANSACTION t
JOIN ACCOUNT a ON t.AccountID = a.AccountID
JOIN BRANCH b ON a.BranchID = b.BranchID
LEFT JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID AND ah.HolderType = 'Primary'
LEFT JOIN CUSTOMER c ON ah.CustomerID = c.CustomerID;

-- View 3: Summary of branch deposits and loans
CREATE OR REPLACE VIEW vw_branch_summary AS
SELECT 
    b.BranchID,
    b.BranchName,
    b.City,
    b.IFSCCode,
    COUNT(DISTINCT a.AccountID) AS TotalAccounts,
    COALESCE(SUM(a.Balance), 0.00) AS TotalDeposits,
    COUNT(DISTINCT l.LoanID) AS TotalLoans,
    COALESCE(SUM(l.LoanAmount), 0.00) AS TotalLoanDisbursed,
    COUNT(DISTINCT e.EmployeeID) AS TotalEmployees
FROM BRANCH b
LEFT JOIN ACCOUNT a ON b.BranchID = a.BranchID
LEFT JOIN LOAN l ON b.BranchID = l.BranchID
LEFT JOIN EMPLOYEE e ON b.BranchID = e.BranchID
GROUP BY b.BranchID, b.BranchName, b.City, b.IFSCCode;

DELIMITER $$

-- Function to calculate total balance of a customer across all their accounts
CREATE FUNCTION fn_customer_total_balance(p_cust_id INT)
RETURNS DECIMAL(15, 2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE total_bal DECIMAL(15, 2);
    SELECT COALESCE(SUM(a.Balance), 0.00)
    INTO total_bal
    FROM ACCOUNT a
    JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID
    WHERE ah.CustomerID = p_cust_id AND a.Status = 'Active';
    RETURN total_bal;
END$$

-- Function to calculate monthly EMI for a loan using standard EMI formula
CREATE FUNCTION fn_calculate_emi(p_amount DECIMAL(15,2), p_annual_rate DECIMAL(5,2), p_tenure_months INT)
RETURNS DECIMAL(10, 2)
DETERMINISTIC
CONTAINS SQL
BEGIN
    DECLARE r DOUBLE;
    DECLARE emi DOUBLE;
    IF p_annual_rate = 0 OR p_tenure_months = 0 THEN
        RETURN ROUND(p_amount / p_tenure_months, 2);
    END IF;
    SET r = (p_annual_rate / 12.0) / 100.0;
    SET emi = (p_amount * r * POW(1 + r, p_tenure_months)) / (POW(1 + r, p_tenure_months) - 1);
    RETURN ROUND(emi, 2);
END$$

-- Procedure for money transfer with transaction rollback and commit
CREATE PROCEDURE sp_transfer_funds(
    IN p_sender_acc_id INT,
    IN p_receiver_acc_id INT,
    IN p_amount DECIMAL(15,2),
    IN p_description VARCHAR(255),
    OUT p_status_code INT,
    OUT p_status_msg VARCHAR(255)
)
BEGIN
    DECLARE sender_bal DECIMAL(15,2);
    DECLARE sender_status VARCHAR(20);
    DECLARE receiver_status VARCHAR(20);
    DECLARE ref_out VARCHAR(50);
    DECLARE ref_in VARCHAR(50);

    -- check amount
    IF p_amount <= 0 THEN
        SET p_status_code = 400;
        SET p_status_msg = 'Amount must be greater than zero';
    ELSEIF p_sender_acc_id = p_receiver_acc_id THEN
        SET p_status_code = 400;
        SET p_status_msg = 'Sender and Receiver account cannot be same';
    ELSE
        -- start atomic transaction
        START TRANSACTION;

        -- lock sender row
        SELECT Balance, Status INTO sender_bal, sender_status
        FROM ACCOUNT WHERE AccountID = p_sender_acc_id FOR UPDATE;

        -- lock receiver row
        SELECT Status INTO receiver_status
        FROM ACCOUNT WHERE AccountID = p_receiver_acc_id FOR UPDATE;

        IF sender_bal IS NULL OR receiver_status IS NULL THEN
            ROLLBACK;
            SET p_status_code = 404;
            SET p_status_msg = 'Account not found';
        ELSEIF sender_status <> 'Active' OR receiver_status <> 'Active' THEN
            ROLLBACK;
            SET p_status_code = 403;
            SET p_status_msg = 'One of the accounts is not active';
        ELSEIF sender_bal < p_amount THEN
            ROLLBACK;
            SET p_status_code = 400;
            SET p_status_msg = 'Insufficient balance in sender account';
        ELSE
            -- deduct from sender
            UPDATE ACCOUNT SET Balance = Balance - p_amount WHERE AccountID = p_sender_acc_id;

            -- add to receiver
            UPDATE ACCOUNT SET Balance = Balance + p_amount WHERE AccountID = p_receiver_acc_id;

            -- generate ref numbers
            SET ref_out = CONCAT('TXN-TRF-OUT-', UNIX_TIMESTAMP(), '-', FLOOR(RAND() * 1000));
            SET ref_in  = CONCAT('TXN-TRF-IN-',  UNIX_TIMESTAMP(), '-', FLOOR(RAND() * 1000));

            -- insert sender transaction
            INSERT INTO TRANSACTION (AccountID, TransactionType, Amount, Description, ReferenceNumber, TransactionStatus)
            VALUES (p_sender_acc_id, 'TRANSFER_OUT', p_amount, COALESCE(p_description, 'Fund Transfer Out'), ref_out, 'SUCCESS');

            -- insert receiver transaction
            INSERT INTO TRANSACTION (AccountID, TransactionType, Amount, Description, ReferenceNumber, TransactionStatus)
            VALUES (p_receiver_acc_id, 'TRANSFER_IN', p_amount, 'Received Fund Transfer', ref_in, 'SUCCESS');

            COMMIT;
            SET p_status_code = 200;
            SET p_status_msg = 'Transfer successful';
        END IF;
    END IF;
END$$

-- Procedure for cash deposit
CREATE PROCEDURE sp_deposit_money(
    IN p_acc_id INT,
    IN p_amount DECIMAL(15,2),
    IN p_desc VARCHAR(255),
    OUT p_status_code INT,
    OUT p_status_msg VARCHAR(255)
)
BEGIN
    DECLARE acc_status VARCHAR(20);
    DECLARE ref_num VARCHAR(50);

    IF p_amount <= 0 THEN
        SET p_status_code = 400;
        SET p_status_msg = 'Deposit amount must be greater than zero';
    ELSE
        START TRANSACTION;
        SELECT Status INTO acc_status FROM ACCOUNT WHERE AccountID = p_acc_id FOR UPDATE;

        IF acc_status IS NULL THEN
            ROLLBACK;
            SET p_status_code = 404;
            SET p_status_msg = 'Account not found';
        ELSEIF acc_status <> 'Active' THEN
            ROLLBACK;
            SET p_status_code = 403;
            SET p_status_msg = 'Account is not active';
        ELSE
            UPDATE ACCOUNT SET Balance = Balance + p_amount WHERE AccountID = p_acc_id;
            SET ref_num = CONCAT('TXN-DEP-', UNIX_TIMESTAMP(), '-', FLOOR(RAND() * 1000));
            INSERT INTO TRANSACTION (AccountID, TransactionType, Amount, Description, ReferenceNumber, TransactionStatus)
            VALUES (p_acc_id, 'DEPOSIT', p_amount, COALESCE(p_desc, 'Cash Deposit'), ref_num, 'SUCCESS');
            COMMIT;
            SET p_status_code = 200;
            SET p_status_msg = 'Deposit successful';
        END IF;
    END IF;
END$$

-- Procedure for cash withdrawal
CREATE PROCEDURE sp_withdraw_money(
    IN p_acc_id INT,
    IN p_amount DECIMAL(15,2),
    IN p_desc VARCHAR(255),
    OUT p_status_code INT,
    OUT p_status_msg VARCHAR(255)
)
BEGIN
    DECLARE cur_bal DECIMAL(15,2);
    DECLARE acc_status VARCHAR(20);
    DECLARE ref_num VARCHAR(50);

    IF p_amount <= 0 THEN
        SET p_status_code = 400;
        SET p_status_msg = 'Withdrawal amount must be greater than zero';
    ELSE
        START TRANSACTION;
        SELECT Balance, Status INTO cur_bal, acc_status FROM ACCOUNT WHERE AccountID = p_acc_id FOR UPDATE;

        IF cur_bal IS NULL THEN
            ROLLBACK;
            SET p_status_code = 404;
            SET p_status_msg = 'Account not found';
        ELSEIF acc_status <> 'Active' THEN
            ROLLBACK;
            SET p_status_code = 403;
            SET p_status_msg = 'Account is not active';
        ELSEIF cur_bal < p_amount THEN
            ROLLBACK;
            SET p_status_code = 400;
            SET p_status_msg = 'Insufficient balance';
        ELSE
            UPDATE ACCOUNT SET Balance = Balance - p_amount WHERE AccountID = p_acc_id;
            SET ref_num = CONCAT('TXN-WTH-', UNIX_TIMESTAMP(), '-', FLOOR(RAND() * 1000));
            INSERT INTO TRANSACTION (AccountID, TransactionType, Amount, Description, ReferenceNumber, TransactionStatus)
            VALUES (p_acc_id, 'WITHDRAWAL', p_amount, COALESCE(p_desc, 'Cash Withdrawal'), ref_num, 'SUCCESS');
            COMMIT;
            SET p_status_code = 200;
            SET p_status_msg = 'Withdrawal successful';
        END IF;
    END IF;
END$$

-- Trigger 1: Don't allow balance to become negative
CREATE TRIGGER trg_prevent_negative_balance
BEFORE UPDATE ON ACCOUNT
FOR EACH ROW
BEGIN
    IF NEW.Balance < 0.00 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Account balance cannot be negative!';
    END IF;
END$$

-- Trigger 2: Check if loan is completely paid, if yes set status to Closed
CREATE TRIGGER trg_check_loan_completion
AFTER INSERT ON LOAN_PAYMENT
FOR EACH ROW
BEGIN
    DECLARE total_paid DECIMAL(15,2);
    DECLARE orig_loan DECIMAL(15,2);

    SELECT COALESCE(SUM(Amount), 0.00) INTO total_paid
    FROM LOAN_PAYMENT WHERE LoanID = NEW.LoanID;

    SELECT LoanAmount INTO orig_loan
    FROM LOAN WHERE LoanID = NEW.LoanID;

    IF total_paid >= orig_loan THEN
        UPDATE LOAN SET LoanStatus = 'Closed' WHERE LoanID = NEW.LoanID;
    END IF;
END$$

DELIMITER ;

-- Insert Branches
INSERT INTO BRANCH (BranchName, IFSCCode, Address, City, State, ContactNumber) VALUES
('Kashi Main Branch', 'KASH0001001', 'Godowlia Chowk, Dashashwamedh', 'Varanasi', 'Uttar Pradesh', '0542-2456781'),
('Assi Ghat Sub-Branch', 'KASH0001002', 'B-12 Nagwa, Near Assi Ghat', 'Varanasi', 'Uttar Pradesh', '0542-2456782'),
('Sarnath Branch', 'KASH0001003', 'Museum Road, Sarnath', 'Varanasi', 'Uttar Pradesh', '0542-2456783'),
('BHU Campus Branch', 'KASH0001004', 'Banaras Hindu University Campus', 'Varanasi', 'Uttar Pradesh', '0542-2456784'),
('Lucknow Hazratganj', 'KASH0001005', 'MG Road, Hazratganj', 'Lucknow', 'Uttar Pradesh', '0522-2287900');

-- Insert Employees
INSERT INTO EMPLOYEE (EmployeeName, Mobile, Email, Designation, Salary, JoiningDate, BranchID) VALUES
('Amitabh Tripathi', '9876543210', 'amitabh.t@kashibank.in', 'Branch Manager', 85000.00, '2020-01-15', 1),
('Sunita Sharma', '9876543211', 'sunita.s@kashibank.in', 'Assistant Manager', 62000.00, '2021-03-10', 1),
('Rahul Verma', '9876543212', 'rahul.v@kashibank.in', 'Cashier', 42000.00, '2022-07-01', 1),
('Pooja Mishra', '9876543213', 'pooja.m@kashibank.in', 'Loan Officer', 58000.00, '2021-09-15', 2),
('Vikramaditya Rao', '9876543214', 'vikram.r@kashibank.in', 'Branch Manager', 82000.00, '2019-11-20', 3),
('Neha Kulkarni', '9876543215', 'neha.k@kashibank.in', 'Clerk', 45000.00, '2023-02-01', 4),
('Rajesh Pandey', '9876543216', 'rajesh.p@kashibank.in', 'Branch Manager', 90000.00, '2018-05-12', 5);

-- Insert Customers
INSERT INTO CUSTOMER (FirstName, LastName, DateOfBirth, Gender, Mobile, Email, Address, City, RegistrationDate) VALUES
('Rohan', 'Gupta', '1998-04-12', 'Male', '9123456780', 'rohan.gupta@example.com', 'Flat 402, Ganga Heights, Lanka', 'Varanasi', '2024-01-10 10:30:00'),
('Priya', 'Singh', '1995-08-25', 'Female', '9123456781', 'priya.singh@example.com', '12/A Chetganj', 'Varanasi', '2024-02-14 11:15:00'),
('Aditya', 'Pandey', '2001-12-05', 'Male', '9123456782', 'aditya.pandey@example.com', 'Hostel 4, IIT BHU Campus', 'Varanasi', '2024-03-01 09:45:00'),
('Ananya', 'Shukla', '1992-06-18', 'Female', '9123456783', 'ananya.s@example.com', 'B-45 Ravindrapuri Colony', 'Varanasi', '2024-03-20 14:20:00'),
('Suresh', 'Yadav', '1985-03-30', 'Male', '9123456784', 'suresh.yadav@example.com', 'Village Shivpur', 'Varanasi', '2024-04-05 16:00:00'),
('Deepak', 'Agarwal', '1990-11-15', 'Male', '9123456785', 'deepak.a@example.com', 'Shop 18, Chowk Bazar', 'Varanasi', '2024-05-12 12:30:00'),
('Sneha', 'Tiwari', '1999-09-09', 'Female', '9123456786', 'sneha.tiwari@example.com', 'Civil Lines', 'Lucknow', '2024-06-01 10:00:00');

-- Insert Accounts
INSERT INTO ACCOUNT (AccountNumber, AccountType, OpeningDate, Balance, Status, BranchID) VALUES
('1001002001', 'Saving', '2024-01-10', 45000.00, 'Active', 1),
('1001002002', 'Salary', '2024-02-14', 85000.00, 'Active', 1),
('1001002003', 'Saving', '2024-03-01', 12500.00, 'Active', 4),
('1001002004', 'Current', '2024-03-20', 175000.00, 'Active', 2),
('1001002005', 'Saving', '2024-04-05', 3500.00, 'Active', 3),
('1001002006', 'Current', '2024-05-12', 250000.00, 'Active', 1),
('1001002007', 'Saving', '2024-06-01', 62000.00, 'Active', 5),
('1001002008', 'Saving', '2024-06-15', 500.00, 'Inactive', 2);

-- Link Customers and Accounts
INSERT INTO ACCOUNT_HOLDER (CustomerID, AccountID, HolderSince, HolderType) VALUES
(1, 1, '2024-01-10', 'Primary'),
(2, 2, '2024-02-14', 'Primary'),
(3, 3, '2024-03-01', 'Primary'),
(4, 4, '2024-03-20', 'Primary'),
(5, 5, '2024-04-05', 'Primary'),
(6, 6, '2024-05-12', 'Primary'),
(7, 7, '2024-06-01', 'Primary'),
(1, 8, '2024-06-15', 'Secondary');

-- Insert Transactions
INSERT INTO TRANSACTION (AccountID, TransactionType, Amount, TransactionDate, Description, ReferenceNumber, TransactionStatus) VALUES
(1, 'DEPOSIT', 50000.00, '2024-01-10 11:00:00', 'Account Opening Deposit', 'TXN-INIT-1001', 'SUCCESS'),
(1, 'WITHDRAWAL', 5000.00, '2024-01-20 14:30:00', 'ATM Cash Withdrawal', 'TXN-ATM-1002', 'SUCCESS'),
(2, 'DEPOSIT', 85000.00, '2024-02-14 12:00:00', 'Salary Credit', 'TXN-SAL-2001', 'SUCCESS'),
(3, 'DEPOSIT', 15000.00, '2024-03-01 10:15:00', 'Cash Deposit', 'TXN-DEP-3001', 'SUCCESS'),
(3, 'WITHDRAWAL', 2500.00, '2024-03-15 17:45:00', 'Hostel Mess Fee', 'TXN-WTH-3002', 'SUCCESS'),
(4, 'DEPOSIT', 200000.00, '2024-03-20 15:00:00', 'Business Payment', 'TXN-DEP-4001', 'SUCCESS'),
(4, 'TRANSFER_OUT', 25000.00, '2024-04-01 11:10:00', 'Transfer to Acc 6', 'TXN-TRF-4002', 'SUCCESS'),
(6, 'TRANSFER_IN', 25000.00, '2024-04-01 11:10:00', 'Transfer from Acc 4', 'TXN-TRF-6001', 'SUCCESS'),
(6, 'DEPOSIT', 225000.00, '2024-05-12 13:00:00', 'Cheque Clearing', 'TXN-CHQ-6002', 'SUCCESS'),
(7, 'DEPOSIT', 62000.00, '2024-06-01 10:30:00', 'Opening Deposit', 'TXN-DEP-7001', 'SUCCESS');

-- Insert Loans
INSERT INTO LOAN (CustomerID, BranchID, LoanType, LoanAmount, InterestRate, StartDate, TenureMonths, LoanStatus) VALUES
(1, 1, 'Vehicle Loan', 450000.00, 8.50, '2024-02-01', 36, 'Disbursed'),
(2, 1, 'Home Loan', 3500000.00, 7.25, '2024-03-01', 180, 'Disbursed'),
(3, 4, 'Education Loan', 800000.00, 6.75, '2024-04-01', 60, 'Disbursed'),
(4, 2, 'Personal Loan', 200000.00, 11.50, '2024-05-15', 24, 'Disbursed');

-- Insert Loan Payments
INSERT INTO LOAN_PAYMENT (LoanID, PaymentDate, Amount, PaymentMode, ReferenceNumber) VALUES
(1, '2024-03-05 10:00:00', 14200.00, 'NetBanking', 'LPAY-VL-001'),
(1, '2024-04-05 10:30:00', 14200.00, 'UPI', 'LPAY-VL-002'),
(2, '2024-04-10 11:15:00', 32000.00, 'NetBanking', 'LPAY-HL-001'),
(3, '2024-05-02 09:45:00', 15700.00, 'NetBanking', 'LPAY-EL-001');
