-- Strict mode helps catch bad inserts/implicit truncation
SET sql_mode = 'STRICT_ALL_TABLES';

-- Target database
CREATE DATABASE IF NOT EXISTS adviseme
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE adviseme;

-- Temporarily relax FK checks while creating the schema
SET FOREIGN_KEY_CHECKS = 0;

-- =====================
-- Tables (in dependency order)
-- =====================

CREATE TABLE IF NOT EXISTS users ( 
    userID       INT PRIMARY KEY AUTO_INCREMENT,
    username     VARCHAR(100) NOT NULL UNIQUE,
    email        VARCHAR(255) NOT NULL UNIQUE,
    role         VARCHAR(32)  NOT NULL,
    isActive     TINYINT      NOT NULL DEFAULT 1,
    createdDate  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT checkRoles CHECK (role IN ('STUDENT', 'ADVISOR', 'ADMIN'))
);

CREATE TABLE IF NOT EXISTS adviseeProfile (
  adviseeID    INT PRIMARY KEY AUTO_INCREMENT,
  userID       INT NOT NULL,
  major        VARCHAR(120),
  status       VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
  createdWhen  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT advisee_user_fk FOREIGN KEY (userID) REFERENCES users(userID)
);

CREATE TABLE IF NOT EXISTS advisorProfile (
    degreePlanID    INT PRIMARY KEY AUTO_INCREMENT,
    adviseeID       INT NOT NULL,
    name            VARCHAR(160) NOT NULL,
    catalog         VARCHAR(32),
    status          VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    createdWhen     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT degreePlanAdvisee FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID)
);

CREATE TABLE IF NOT EXISTS terms (
    termID      INT PRIMARY KEY AUTO_INCREMENT,
    code        VARCHAR(32) NOT NULL,
    startDate   DATETIME NOT NULL,
    endDate     DATETIME NOT NULL,
    CONSTRAINT  checkTerm CHECK (endDate > startDate)
);

CREATE TABLE IF NOT EXISTS courses (
    courseID        INT PRIMARY KEY AUTO_INCREMENT,
    courseName      VARCHAR(160) NOT NULL,
    description     TEXT,
    credits         INT NOT NULL,
    CONSTRAINT checkCredits CHECK (credits > 0)
);

CREATE TABLE IF NOT EXISTS sections (
    sectionID       INT PRIMARY KEY AUTO_INCREMENT,
    courseID        INT NOT NULL,
    termID          INT NOT NULL,
    crn             VARCHAR(32) NOT NULL UNIQUE,
    capacity        INT NOT NULL,
    enrolled        INT NOT NULL DEFAULT 0,
    professorName   VARCHAR(160),
    status          VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    description     TEXT,
    CONSTRAINT sectionCourses FOREIGN KEY (courseID) REFERENCES courses(courseID),
    CONSTRAINT sectionTerm    FOREIGN KEY (termID)   REFERENCES terms(termID),
    CONSTRAINT enrolledCapacity CHECK (enrolled <= capacity) 
);

CREATE TABLE IF NOT EXISTS schedules (
    scheduleID      INT PRIMARY KEY AUTO_INCREMENT, 
    adviseeID       INT NOT NULL,
    termID          INT NOT NULL,
    source          VARCHAR(32) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
    createdWhen     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approvedWhen    DATETIME,
    rejectedWhen    DATETIME,
    CONSTRAINT scheduleAdvisee FOREIGN KEY (adviseeID) REFERENCES adviseeProfile (adviseeID),
    CONSTRAINT scheduleTerm    FOREIGN KEY (termID)    REFERENCES terms(termID),
    CONSTRAINT scheduleDate CHECK (
        (approvedWhen IS NULL OR approvedWhen >= createdWhen) AND 
        (rejectedWhen IS NULL OR rejectedWhen >= createdWhen)
    )
);

CREATE TABLE IF NOT EXISTS classes (
    classID     INT PRIMARY KEY AUTO_INCREMENT, 
    sectionID   INT NOT NULL,
    scheduleID  INT NOT NULL,
    createdDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT classSection  FOREIGN KEY (sectionID)  REFERENCES sections(sectionID),
    CONSTRAINT classSchedule FOREIGN KEY (scheduleID) REFERENCES schedules(scheduleID),
    UNIQUE KEY scheduleSection (scheduleID, sectionID)
);

CREATE TABLE IF NOT EXISTS enrollments (
    enrollmentID    INT PRIMARY KEY AUTO_INCREMENT, 
    adviseeID       INT NOT NULL,
    sectionID       INT NOT NULL,
    courseID        INT NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'ENROLLED',
    grade           VARCHAR(8),
    creditsEarned   INT NOT NULL,
    attemptedNumber INT NOT NULL,
    createdWhen     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT enrolledAdvisee FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID),
    CONSTRAINT enrolledSection FOREIGN KEY (sectionID) REFERENCES sections(sectionID),
    CONSTRAINT enrolledCourse  FOREIGN KEY (courseID)  REFERENCES courses(courseID),
    CONSTRAINT enrollAdviseeSection UNIQUE (adviseeID, sectionID)
);

CREATE TABLE IF NOT EXISTS notifications (
    notificationID  INT PRIMARY KEY AUTO_INCREMENT,
    userID          INT NOT NULL,
    description     VARCHAR(500) NOT NULL,
    createdAt       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT notificationUser FOREIGN KEY (userID) REFERENCES users(userID)
);

-- Re-enable FK checks after all tables exist
SET FOREIGN_KEY_CHECKS = 1;

-- =====================
-- Seed data
-- =====================

-- USERS
INSERT INTO users (userID, username, email, role, isActive)
VALUES
(1, 'admin_user',    'admin@adviseme.edu',    'ADMIN',   1),
(2, 'advisor_jones', 'jones@adviseme.edu',    'ADVISOR', 1),
(3, 'student_smith', 'smith@student.edu',     'STUDENT', 1),
(4, 'student_lee',   'lee@student.edu',       'STUDENT', 1)
ON DUPLICATE KEY UPDATE username=VALUES(username);

-- ADVISEE PROFILE (map students -> adviseeIDs used below)
INSERT INTO adviseeProfile (adviseeID, userID, major)
VALUES
(101, 3, 'Computer Science BS'),
(102, 4, 'Software Engineering BS')
ON DUPLICATE KEY UPDATE userID=VALUES(userID);

-- TERMS
INSERT INTO terms (termID, code, startDate, endDate)
VALUES
(1, 'FA25', '2025-08-19', '2025-12-12'),
(2, 'SP26', '2026-01-13', '2026-05-05')
ON DUPLICATE KEY UPDATE code=VALUES(code);

-- COURSES
INSERT INTO courses (courseID, courseName, description, credits)
VALUES
(101, 'CS 101 Introduction to Programming', 'Introductory course in Python programming', 3),
(102, 'CS 201 Data Structures',             'Covers arrays, linked lists, trees, and graphs', 4),
(103, 'MATH 140 Calculus I',                'Fundamentals of differential and integral calculus', 4)
ON DUPLICATE KEY UPDATE courseName=VALUES(courseName);

-- SECTIONS
INSERT INTO sections (sectionID, courseID, termID, crn, capacity, enrolled, professorName, status, description)
VALUES
(1, 101, 1, 'CRN1001', 30, 25, 'Dr. Brown',  'OPEN',   'Morning section'),
(2, 102, 1, 'CRN1002', 25, 22, 'Dr. Wilson', 'OPEN',   'Afternoon section'),
(3, 103, 1, 'CRN1003', 30, 29, 'Dr. Kim',    'CLOSED', 'Full section')
ON DUPLICATE KEY UPDATE crn=VALUES(crn);

-- SCHEDULES
INSERT INTO schedules (scheduleID, adviseeID, termID, source, status)
VALUES
(1, 101, 1, 'WEB_PORTAL',          'DRAFT'),
(2, 102, 1, 'ADVISOR_RECOMMENDED', 'APPROVED')
ON DUPLICATE KEY UPDATE status=VALUES(status);

-- CLASSES
INSERT INTO classes (classID, sectionID, scheduleID)
VALUES
(1, 1, 1),
(2, 2, 1),
(3, 3, 2)
ON DUPLICATE KEY UPDATE sectionID=VALUES(sectionID);

-- ENROLLMENTS
INSERT INTO enrollments (enrollmentID, adviseeID, sectionID, courseID, status, grade, creditsEarned, attemptedNumber)
VALUES
(1, 101, 1, 101, 'ENROLLED',  NULL, 3, 1),
(2, 101, 2, 102, 'ENROLLED',  NULL, 4, 1),
(3, 102, 3, 103, 'COMPLETED', 'A',  4, 1)
ON DUPLICATE KEY UPDATE status=VALUES(status);

-- ADVISOR PROFILE
INSERT INTO advisorProfile (degreePlanID, adviseeID, name, catalog)
VALUES
(1, 101, 'Computer Science BS',  '2025-2026'),
(2, 102, 'Software Engineering BS','2025-2026')
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- NOTIFICATIONS
INSERT INTO notifications (notificationID, userID, description)
VALUES
(1, 3, 'Your schedule for Fall 2025 has been drafted.'),
(2, 2, 'Advisee Smith submitted schedule for approval.'),
(3, 1, 'New advisor account created.')
ON DUPLICATE KEY UPDATE description=VALUES(description);
