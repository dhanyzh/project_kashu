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
