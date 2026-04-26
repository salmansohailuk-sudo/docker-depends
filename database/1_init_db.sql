-- Run this once against your RDS MySQL instance to create the database and table.
-- The application (SQLAlchemy) will auto-create the user_entity table on first start,
-- but you still need the database itself to exist first.

CREATE DATABASE IF NOT EXISTS backend_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE backend_db;

-- Optional: pre-create the table explicitly (Flask/SQLAlchemy will also do this automatically)
CREATE TABLE IF NOT EXISTS user_entity (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    full_name    VARCHAR(255) NOT NULL,
    email        VARCHAR(255) NOT NULL UNIQUE,
    phone_number VARCHAR(20)  NOT NULL
);
