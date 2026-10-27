-- Project: Shreehari Finance
-- DBMS Lab (3rd Sem B.Tech CSE)

DROP DATABASE IF EXISTS project_kashi;
CREATE DATABASE project_kashi;
USE project_kashi;

-- 1. Branch table
CREATE TABLE BRANCH (
    BranchID INT AUTO_INCREMENT PRIMARY KEY,
    BranchName VARCHAR(100) NOT NULL,
    IFSCCode VARCHAR(20) NOT NULL UNIQUE,
    Address VARCHAR(255) NOT NULL,
    City VARCHAR(50) NOT NULL,
    State VARCHAR(50) NOT NULL,
    ContactNumber VARCHAR(15) NOT NULL
);

-- 2. Customer table
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
    RegistrationDate DATE DEFAULT (CURRENT_DATE)
);

-- 3. Employee table
CREATE TABLE EMPLOYEE (
    EmployeeID INT AUTO_INCREMENT PRIMARY KEY,
    EmployeeName VARCHAR(100) NOT NULL,
    Mobile VARCHAR(15) NOT NULL,
    Email VARCHAR(100) NOT NULL UNIQUE,
    Designation VARCHAR(50) NOT NULL,
    Salary DECIMAL(10, 2) NOT NULL CHECK (Salary > 0),
    JoiningDate DATE NOT NULL,
    BranchID INT NOT NULL,
    FOREIGN KEY (BranchID) REFERENCES BRANCH(BranchID)
);

-- 4. Account table
CREATE TABLE ACCOUNT (
    AccountID INT AUTO_INCREMENT PRIMARY KEY,
    AccountNumber VARCHAR(20) NOT NULL UNIQUE,
    AccountType ENUM('Saving', 'Current', 'Salary') NOT NULL,
    OpeningDate DATE NOT NULL,
    Balance DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    Status ENUM('Active', 'Inactive', 'Close') NOT NULL DEFAULT 'Active',
    BranchID INT NOT NULL,
    FOREIGN KEY (BranchID) REFERENCES BRANCH(BranchID)
);

-- 5. Account Holder table (m:n relation)
CREATE TABLE ACCOUNT_HOLDER (
    CustomerID INT NOT NULL,
    AccountID INT NOT NULL,
    HolderSince DATE NOT NULL,
    HolderType VARCHAR(20) DEFAULT 'Primary',
    PRIMARY KEY (CustomerID, AccountID),
    FOREIGN KEY (CustomerID) REFERENCES CUSTOMER(CustomerID) ON DELETE CASCADE,
    FOREIGN KEY (AccountID) REFERENCES ACCOUNT(AccountID) ON DELETE CASCADE
);

-- 6. Transaction table
CREATE TABLE TRANSACTION (
    TransactionID INT AUTO_INCREMENT PRIMARY KEY,
    AccountID INT NOT NULL,
    TransactionType ENUM('DEPOSIT', 'WITHDRAWAL', 'TRANSFER_IN', 'TRANSFER_OUT') NOT NULL,
    Amount DECIMAL(12, 2) NOT NULL CHECK (Amount > 0),
    TransactionDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    Description VARCHAR(255),
    ReferenceNumber VARCHAR(50) NOT NULL UNIQUE,
    TransactionStatus VARCHAR(20) DEFAULT 'SUCCESS',
    FOREIGN KEY (AccountID) REFERENCES ACCOUNT(AccountID)
);

-- 7. Loan table
CREATE TABLE LOAN (
    LoanID INT AUTO_INCREMENT PRIMARY KEY,
    CustomerID INT NOT NULL,
    BranchID INT NOT NULL,
    LoanType VARCHAR(50) NOT NULL,
    LoanAmount DECIMAL(12, 2) NOT NULL,
    InterestRate DECIMAL(5, 2) NOT NULL,
    StartDate DATE NOT NULL,
    TenureMonths INT NOT NULL,
    LoanStatus VARCHAR(20) DEFAULT 'Disbursed',
    FOREIGN KEY (CustomerID) REFERENCES CUSTOMER(CustomerID),
    FOREIGN KEY (BranchID) REFERENCES BRANCH(BranchID)
);

-- 8. Loan Payment table
CREATE TABLE LOAN_PAYMENT (
    PaymentID INT AUTO_INCREMENT PRIMARY KEY,
    LoanID INT NOT NULL,
    PaymentDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    Amount DECIMAL(12, 2) NOT NULL,
    PaymentMode VARCHAR(30) NOT NULL,
    ReferenceNumber VARCHAR(50) NOT NULL UNIQUE,
    FOREIGN KEY (LoanID) REFERENCES LOAN(LoanID)
);

-- View: Customer and their account details
CREATE VIEW vw_customer_accounts AS
SELECT c.CustomerID, CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName,
       c.Mobile, a.AccountNumber, a.AccountType, a.Balance, b.BranchName
FROM CUSTOMER c
JOIN ACCOUNT_HOLDER ah ON c.CustomerID = ah.CustomerID
JOIN ACCOUNT a ON ah.AccountID = a.AccountID
JOIN BRANCH b ON a.BranchID = b.BranchID;

DELIMITER $$

-- Trigger: Prevent negative account balance
CREATE TRIGGER trg_prevent_negative_balance
BEFORE UPDATE ON ACCOUNT
FOR EACH ROW
BEGIN
    IF NEW.Balance < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Account balance cannot be negative';
    END IF;
END$$

-- Stored Procedure: Money transfer with ACID transaction
CREATE PROCEDURE sp_transfer_funds(
    IN p_sender_id INT,
    IN p_receiver_id INT,
    IN p_amount DECIMAL(12,2),
    IN p_desc VARCHAR(255),
    OUT p_status_code INT,
    OUT p_status_msg VARCHAR(255)
)
BEGIN
    DECLARE sender_bal DECIMAL(12,2);

    IF p_amount <= 0 THEN
        SET p_status_code = 400;
        SET p_status_msg = 'Amount must be greater than zero';
    ELSEIF p_sender_id = p_receiver_id THEN
        SET p_status_code = 400;
        SET p_status_msg = 'Sender and Receiver cannot be same account';
    ELSE
        START TRANSACTION;
        SELECT Balance INTO sender_bal FROM ACCOUNT WHERE AccountID = p_sender_id FOR UPDATE;

        IF sender_bal >= p_amount THEN
            UPDATE ACCOUNT SET Balance = Balance - p_amount WHERE AccountID = p_sender_id;
            UPDATE ACCOUNT SET Balance = Balance + p_amount WHERE AccountID = p_receiver_id;

            INSERT INTO TRANSACTION (AccountID, TransactionType, Amount, Description, ReferenceNumber)
            VALUES (p_sender_id, 'TRANSFER_OUT', p_amount, p_desc, CONCAT('TXN-OUT-', UNIX_TIMESTAMP()));

            INSERT INTO TRANSACTION (AccountID, TransactionType, Amount, Description, ReferenceNumber)
            VALUES (p_receiver_id, 'TRANSFER_IN', p_amount, p_desc, CONCAT('TXN-IN-', UNIX_TIMESTAMP()));

            COMMIT;
            SET p_status_code = 200;
            SET p_status_msg = 'Transfer successful';
        ELSE
            ROLLBACK;
            SET p_status_code = 400;
            SET p_status_msg = 'Insufficient balance in sender account';
        END IF;
    END IF;
END$$

DELIMITER ;

-- Insert sample branches
INSERT INTO BRANCH (BranchName, IFSCCode, Address, City, State, ContactNumber) VALUES
('Shreehari Branch 1', 'SHRE0001001', 'Godowlia Chowk', 'Varanasi', 'Uttar Pradesh', '0542-2456781'),
('Shreehari Branch 2', 'SHRE0001002', 'Near Assi Ghat', 'Varanasi', 'Uttar Pradesh', '0542-2456782'),
('Shreehari Branch 3', 'SHRE0001003', 'Museum Road, Sarnath', 'Varanasi', 'Uttar Pradesh', '0542-2456783');

-- Insert sample employees
INSERT INTO EMPLOYEE (EmployeeName, Mobile, Email, Designation, Salary, JoiningDate, BranchID) VALUES
('Amitabh Tripathi', '9876543210', 'amitabh@shreehari.in', 'Branch Manager', 75000.00, '2021-01-10', 1),
('Sunita Sharma', '9876543211', 'sunita@shreehari.in', 'Cashier', 40000.00, '2022-03-15', 1),
('Rahul Verma', '9876543212', 'rahul@shreehari.in', 'Assistant Manager', 55000.00, '2021-06-20', 2);

-- Insert sample customers
INSERT INTO CUSTOMER (FirstName, LastName, DateOfBirth, Gender, Mobile, Email, Address, City) VALUES
('Rohan', 'Gupta', '1998-04-12', 'Male', '9123456780', 'rohan@gmail.com', 'Lanka', 'Varanasi'),
('Priya', 'Singh', '1995-08-25', 'Female', '9123456781', 'priya@gmail.com', 'Chetganj', 'Varanasi'),
('Aditya', 'Pandey', '2001-12-05', 'Male', '9123456782', 'aditya@gmail.com', 'BHU Campus', 'Varanasi'),
('Ananya', 'Shukla', '1992-06-18', 'Female', '9123456783', 'ananya@gmail.com', 'Ravindrapuri', 'Varanasi');

-- Insert sample accounts
INSERT INTO ACCOUNT (AccountNumber, AccountType, OpeningDate, Balance, Status, BranchID) VALUES
('1001002001', 'Saving', '2024-01-10', 45000.00, 'Active', 1),
('1001002002', 'Salary', '2024-02-14', 85000.00, 'Active', 1),
('1001002003', 'Saving', '2024-03-01', 12500.00, 'Active', 2),
('1001002004', 'Current', '2024-03-20', 175000.00, 'Active', 3);

-- Link customers to accounts
INSERT INTO ACCOUNT_HOLDER (CustomerID, AccountID, HolderSince, HolderType) VALUES
(1, 1, '2024-01-10', 'Primary'),
(2, 2, '2024-02-14', 'Primary'),
(3, 3, '2024-03-01', 'Primary'),
(4, 4, '2024-03-20', 'Primary');

-- Insert sample transactions
INSERT INTO TRANSACTION (AccountID, TransactionType, Amount, Description, ReferenceNumber) VALUES
(1, 'DEPOSIT', 45000.00, 'Account Opening Deposit', 'TXN-INIT-101'),
(2, 'DEPOSIT', 85000.00, 'Initial Salary Credit', 'TXN-INIT-102'),
(3, 'DEPOSIT', 15000.00, 'Cash Deposit', 'TXN-INIT-103'),
(3, 'WITHDRAWAL', 2500.00, 'ATM Cash Withdrawal', 'TXN-WTH-104');

-- Insert sample loans
INSERT INTO LOAN (CustomerID, BranchID, LoanType, LoanAmount, InterestRate, StartDate, TenureMonths, LoanStatus) VALUES
(1, 1, 'Vehicle Loan', 300000.00, 8.50, '2024-02-01', 36, 'Disbursed'),
(2, 2, 'Home Loan', 1500000.00, 7.50, '2024-03-10', 120, 'Disbursed');

-- Insert sample loan payments
INSERT INTO LOAN_PAYMENT (LoanID, Amount, PaymentMode, ReferenceNumber) VALUES
(1, 9500.00, 'NetBanking', 'LPAY-001'),
(2, 18000.00, 'UPI', 'LPAY-002');
