DROP DATABASE IF EXISTS project_kashi;
CREATE DATABASE project_kashi;
USE project_kashi;

CREATE TABLE IF NOT EXISTS CUSTOMER (
    CustomerID INT AUTO_INCREMENT PRIMARY KEY,
    FirstName VARCHAR(50) NOT NULL,
    LastName VARCHAR(50) NOT NULL,
    DateOfBirth DATE,
    Gender VARCHAR(20),
    Mobile VARCHAR(15) NOT NULL UNIQUE,
    Email VARCHAR(100) UNIQUE,
    Address VARCHAR(255),
    City VARCHAR(80),
    RegistrationDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS BRANCH (
    BranchID INT AUTO_INCREMENT PRIMARY KEY,
    BranchName VARCHAR(100) NOT NULL,
    IFSCCode VARCHAR(20) NOT NULL UNIQUE,
    Address VARCHAR(255) NOT NULL,
    City VARCHAR(80) NOT NULL,
    State VARCHAR(80) NOT NULL,
    ContactNumber VARCHAR(15) NOT NULL
);

CREATE TABLE IF NOT EXISTS EMPLOYEE (
    EmployeeID INT AUTO_INCREMENT PRIMARY KEY,
    EmployeeName VARCHAR(100) NOT NULL,
    Mobile VARCHAR(15) NOT NULL UNIQUE,
    Email VARCHAR(100) UNIQUE,
    Designation VARCHAR(80) NOT NULL,
    Salary DECIMAL(12,2) NOT NULL CHECK (Salary > 0),
    JoiningDate DATE NOT NULL,
    BranchID INT NOT NULL,
    FOREIGN KEY (BranchID) REFERENCES BRANCH(BranchID)
);

CREATE TABLE IF NOT EXISTS ACCOUNT (
    AccountID INT AUTO_INCREMENT PRIMARY KEY,
    AccountNumber VARCHAR(24) NOT NULL UNIQUE,
    AccountType VARCHAR(20) NOT NULL CHECK (AccountType IN ('Saving', 'Current', 'Salary')),
    OpeningDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    Balance DECIMAL(14,2) NOT NULL DEFAULT 0 CHECK (Balance >= 0),
    Status VARCHAR(20) NOT NULL DEFAULT 'Active' CHECK (Status IN ('Active', 'Inactive', 'Close')),
    BranchID INT NOT NULL,
    FOREIGN KEY (BranchID) REFERENCES BRANCH(BranchID)
);

CREATE TABLE IF NOT EXISTS ACCOUNT_HOLDER (
    CustomerID INT NOT NULL,
    AccountID INT NOT NULL,
    HolderSince TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    HolderType VARCHAR(20) DEFAULT 'Primary',
    PRIMARY KEY (CustomerID, AccountID),
    FOREIGN KEY (CustomerID) REFERENCES CUSTOMER(CustomerID) ON DELETE CASCADE,
    FOREIGN KEY (AccountID) REFERENCES ACCOUNT(AccountID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS `TRANSACTION` (
    TransactionID INT AUTO_INCREMENT PRIMARY KEY,
    AccountID INT NOT NULL,
    TransactionType VARCHAR(20) NOT NULL CHECK (TransactionType IN ('DEPOSIT', 'WITHDRAWAL', 'TRANSFER_IN', 'TRANSFER_OUT')),
    Amount DECIMAL(14,2) NOT NULL CHECK (Amount > 0),
    TransactionDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    Description VARCHAR(255),
    ReferenceNumber VARCHAR(40) NOT NULL,
    TransactionStatus VARCHAR(20) DEFAULT 'Success',
    FOREIGN KEY (AccountID) REFERENCES ACCOUNT(AccountID)
);

CREATE TABLE IF NOT EXISTS LOAN (
    LoanID INT AUTO_INCREMENT PRIMARY KEY,
    CustomerID INT NOT NULL,
    BranchID INT NOT NULL,
    LoanType VARCHAR(40) NOT NULL CHECK (LoanType IN ('Home Loan', 'Education Loan', 'Personal Loan', 'Vehicle Loan')),
    LoanAmount DECIMAL(14,2) NOT NULL CHECK (LoanAmount > 0),
    InterestRate DECIMAL(5,2) NOT NULL CHECK (InterestRate >= 0),
    StartDate DATE NOT NULL,
    TenureMonths INT NOT NULL CHECK (TenureMonths > 0),
    LoanStatus VARCHAR(20) DEFAULT 'Pending' CHECK (LoanStatus IN ('Pending', 'Approved', 'Rejected', 'Closed', 'Disbursed')),
    FOREIGN KEY (CustomerID) REFERENCES CUSTOMER(CustomerID),
    FOREIGN KEY (BranchID) REFERENCES BRANCH(BranchID)
);

CREATE TABLE IF NOT EXISTS LOAN_PAYMENT (
    PaymentID INT AUTO_INCREMENT PRIMARY KEY,
    LoanID INT NOT NULL,
    PaymentDate DATE DEFAULT (CURRENT_DATE),
    Amount DECIMAL(14,2) NOT NULL CHECK (Amount > 0),
    PaymentMode VARCHAR(30) NOT NULL,
    ReferenceNumber VARCHAR(40) NOT NULL UNIQUE,
    FOREIGN KEY (LoanID) REFERENCES LOAN(LoanID)
);

-- Initial default branch so branch dropdowns are ready
INSERT IGNORE INTO BRANCH (BranchName, IFSCCode, Address, City, State, ContactNumber)
VALUES ('Kashi Main Branch', 'KASH0001001', '12 River Road', 'Thrissur', 'Kerala', '04871234567');

DELIMITER $$

-- ===================== STORED FUNCTIONS =====================

DROP FUNCTION IF EXISTS fn_get_balance$$
CREATE FUNCTION fn_get_balance(p_account_id INT)
RETURNS DECIMAL(14,2)
READS SQL DATA
BEGIN
    DECLARE v_balance DECIMAL(14,2);
    SELECT Balance INTO v_balance FROM ACCOUNT WHERE AccountID = p_account_id;
    RETURN v_balance;
END$$

DROP FUNCTION IF EXISTS fn_total_paid$$
CREATE FUNCTION fn_total_paid(p_loan_id INT)
RETURNS DECIMAL(14,2)
READS SQL DATA
BEGIN
    DECLARE v_total DECIMAL(14,2);
    SELECT IFNULL(SUM(Amount), 0) INTO v_total FROM LOAN_PAYMENT WHERE LoanID = p_loan_id;
    RETURN v_total;
END$$

DROP FUNCTION IF EXISTS fn_calculate_emi$$
CREATE FUNCTION fn_calculate_emi(p_amount DECIMAL(14,2), p_rate DECIMAL(5,2), p_months INT)
RETURNS DECIMAL(14,2)
DETERMINISTIC
BEGIN
    DECLARE r DOUBLE;
    IF p_rate = 0 THEN
        RETURN ROUND(p_amount / p_months, 2);
    END IF;
    SET r = p_rate / 12 / 100;
    RETURN ROUND(p_amount * r * POW(1 + r, p_months) / (POW(1 + r, p_months) - 1), 2);
END$$

-- ===================== VIEWS =====================

CREATE OR REPLACE VIEW vw_account_summary AS
SELECT a.AccountID, a.AccountNumber, a.AccountType, a.Balance, a.Status, a.OpeningDate,
       b.BranchName, c.CustomerID, CONCAT(c.FirstName, ' ', c.LastName) AS HolderName
FROM ACCOUNT a
JOIN ACCOUNT_HOLDER ah ON a.AccountID = ah.AccountID
JOIN CUSTOMER c ON ah.CustomerID = c.CustomerID
JOIN BRANCH b ON a.BranchID = b.BranchID$$

CREATE OR REPLACE VIEW vw_transaction_history AS
SELECT t.TransactionID, t.AccountID, a.AccountNumber, t.TransactionType, t.Amount,
       t.TransactionDate, t.Description, t.ReferenceNumber, t.TransactionStatus
FROM `TRANSACTION` t
JOIN ACCOUNT a ON t.AccountID = a.AccountID$$

CREATE OR REPLACE VIEW vw_loan_summary AS
SELECT l.LoanID, CONCAT(c.FirstName, ' ', c.LastName) AS CustomerName, b.BranchName,
       l.LoanType, l.LoanAmount, l.InterestRate, l.TenureMonths, l.StartDate, l.LoanStatus,
       fn_calculate_emi(l.LoanAmount, l.InterestRate, l.TenureMonths) AS EMI,
       fn_calculate_emi(l.LoanAmount, l.InterestRate, l.TenureMonths) * l.TenureMonths AS TotalPayable,
       fn_total_paid(l.LoanID) AS TotalPaid
FROM LOAN l
JOIN CUSTOMER c ON l.CustomerID = c.CustomerID
JOIN BRANCH b ON l.BranchID = b.BranchID$$

-- ===================== TRIGGERS =====================

DROP TRIGGER IF EXISTS trg_transaction_before_insert$$
CREATE TRIGGER trg_transaction_before_insert
BEFORE INSERT ON `TRANSACTION`
FOR EACH ROW
BEGIN
    DECLARE v_balance DECIMAL(14,2);
    DECLARE v_status VARCHAR(20);

    IF NEW.Amount <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Amount must be greater than zero';
    END IF;

    SELECT Balance, Status INTO v_balance, v_status FROM ACCOUNT WHERE AccountID = NEW.AccountID;

    IF v_status <> 'Active' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Account is not active';
    END IF;

    IF NEW.TransactionType IN ('WITHDRAWAL', 'TRANSFER_OUT') AND v_balance < NEW.Amount THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Insufficient balance';
    END IF;
END$$

DROP TRIGGER IF EXISTS trg_transaction_after_insert$$
CREATE TRIGGER trg_transaction_after_insert
AFTER INSERT ON `TRANSACTION`
FOR EACH ROW
BEGIN
    IF NEW.TransactionType IN ('DEPOSIT', 'TRANSFER_IN') THEN
        UPDATE ACCOUNT SET Balance = Balance + NEW.Amount WHERE AccountID = NEW.AccountID;
    ELSE
        UPDATE ACCOUNT SET Balance = Balance - NEW.Amount WHERE AccountID = NEW.AccountID;
    END IF;
END$$

DROP TRIGGER IF EXISTS trg_account_before_update$$
CREATE TRIGGER trg_account_before_update
BEFORE UPDATE ON ACCOUNT
FOR EACH ROW
BEGIN
    IF NEW.Status = 'Close' AND OLD.Status <> 'Close' AND NEW.Balance > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Withdraw the balance before closing the account';
    END IF;
END$$

DROP TRIGGER IF EXISTS trg_loan_payment_before_insert$$
CREATE TRIGGER trg_loan_payment_before_insert
BEFORE INSERT ON LOAN_PAYMENT
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(20);
    SELECT LoanStatus INTO v_status FROM LOAN WHERE LoanID = NEW.LoanID;
    IF v_status NOT IN ('Approved', 'Disbursed') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Payments are allowed only for Approved or Disbursed loans';
    END IF;
END$$

DROP TRIGGER IF EXISTS trg_loan_payment_after_insert$$
CREATE TRIGGER trg_loan_payment_after_insert
AFTER INSERT ON LOAN_PAYMENT
FOR EACH ROW
BEGIN
    DECLARE v_payable DECIMAL(14,2);
    SELECT fn_calculate_emi(LoanAmount, InterestRate, TenureMonths) * TenureMonths
    INTO v_payable FROM LOAN WHERE LoanID = NEW.LoanID;
    IF fn_total_paid(NEW.LoanID) >= v_payable THEN
        UPDATE LOAN SET LoanStatus = 'Closed' WHERE LoanID = NEW.LoanID;
    END IF;
END$$

-- ===================== STORED PROCEDURES =====================

DROP PROCEDURE IF EXISTS sp_deposit$$
CREATE PROCEDURE sp_deposit(IN p_account_id INT, IN p_amount DECIMAL(14,2), IN p_description VARCHAR(255))
BEGIN
    INSERT INTO `TRANSACTION` (AccountID, TransactionType, Amount, Description, ReferenceNumber)
    VALUES (p_account_id, 'DEPOSIT', p_amount, p_description,
            CONCAT('TXN', UNIX_TIMESTAMP(), LPAD(FLOOR(RAND() * 10000), 4, '0')));
END$$

DROP PROCEDURE IF EXISTS sp_withdraw$$
CREATE PROCEDURE sp_withdraw(IN p_account_id INT, IN p_amount DECIMAL(14,2), IN p_description VARCHAR(255))
BEGIN
    INSERT INTO `TRANSACTION` (AccountID, TransactionType, Amount, Description, ReferenceNumber)
    VALUES (p_account_id, 'WITHDRAWAL', p_amount, p_description,
            CONCAT('TXN', UNIX_TIMESTAMP(), LPAD(FLOOR(RAND() * 10000), 4, '0')));
END$$

DROP PROCEDURE IF EXISTS sp_transfer$$
CREATE PROCEDURE sp_transfer(IN p_from INT, IN p_to INT, IN p_amount DECIMAL(14,2), IN p_description VARCHAR(255))
BEGIN
    DECLARE v_ref VARCHAR(40);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    IF p_from = p_to THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot transfer to the same account';
    END IF;

    SET v_ref = CONCAT('TRF', UNIX_TIMESTAMP(), LPAD(FLOOR(RAND() * 10000), 4, '0'));

    START TRANSACTION;
    INSERT INTO `TRANSACTION` (AccountID, TransactionType, Amount, Description, ReferenceNumber)
    VALUES (p_from, 'TRANSFER_OUT', p_amount, p_description, v_ref);
    INSERT INTO `TRANSACTION` (AccountID, TransactionType, Amount, Description, ReferenceNumber)
    VALUES (p_to, 'TRANSFER_IN', p_amount, p_description, v_ref);
    COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_open_account$$
CREATE PROCEDURE sp_open_account(IN p_customer_id INT, IN p_branch_id INT, IN p_account_type VARCHAR(20),
                                 IN p_initial DECIMAL(14,2), OUT p_account_id INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    INSERT INTO ACCOUNT (AccountNumber, AccountType, BranchID)
    VALUES (CONCAT('KASH', LPAD(FLOOR(RAND() * 10000000000), 10, '0')), p_account_type, p_branch_id);
    SET p_account_id = LAST_INSERT_ID();

    INSERT INTO ACCOUNT_HOLDER (CustomerID, AccountID, HolderType)
    VALUES (p_customer_id, p_account_id, 'Primary');

    IF p_initial > 0 THEN
        INSERT INTO `TRANSACTION` (AccountID, TransactionType, Amount, Description, ReferenceNumber)
        VALUES (p_account_id, 'DEPOSIT', p_initial, 'Initial deposit',
                CONCAT('TXN', UNIX_TIMESTAMP(), LPAD(FLOOR(RAND() * 10000), 4, '0')));
    END IF;
    COMMIT;
END$$

DELIMITER ;
