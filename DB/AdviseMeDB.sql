-- Create DB & select it
CREATE DATABASE IF NOT EXISTS adviseme;
USE adviseme;

-- ---------- Tables ----------
CREATE TABLE IF NOT EXISTS users (
  userID       INT AUTO_INCREMENT PRIMARY KEY,
  username     VARCHAR(100)  NOT NULL UNIQUE,
  email        VARCHAR(255)  NOT NULL UNIQUE,
  role         ENUM('STUDENT','ADVISOR','ADMIN') NOT NULL,
  isActive     TINYINT(1)    NOT NULL DEFAULT 1,
  createdDate  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT checkRoles CHECK (role IN ('STUDENT','ADVISOR','ADMIN'))
);

CREATE TABLE IF NOT EXISTS advisorProfile (
  advisorID     INT PRIMARY KEY,
  name          VARCHAR(160) NOT NULL,
  office        VARCHAR(160) NULL,
  createdWhen   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fkAdvisorProfileUser FOREIGN KEY (advisorID)
    REFERENCES users(userID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS adviseeProfile (
  adviseeID         INT AUTO_INCREMENT PRIMARY KEY,
  userID            INT NOT NULL UNIQUE,
  advisorID         INT NULL, 
  major             VARCHAR(100) NOT NULL,
  degree_plan       VARCHAR(100),
  classification    ENUM('Freshman','Sophomore','Junior','Senior') NOT NULL,
  gpa               DECIMAL(3,2),
  credits_completed INT DEFAULT 0,
  status            ENUM('Active','Inactive','Graduated','Suspended') DEFAULT 'Active',
  dateCreated       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  lastUpdated       TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_advisee_user FOREIGN KEY (userID)
    REFERENCES users(userID) ON DELETE CASCADE,
  CONSTRAINT fk_advisee_advisor FOREIGN KEY (advisorID)
    REFERENCES advisorProfile(advisorID) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS advisorAdviseeBridge (
  advisorID  INT NOT NULL,
  adviseeID  INT NOT NULL,
  isActive   TINYINT(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (advisorID, adviseeID),
  CONSTRAINT fkBridgeAdvisor  FOREIGN KEY (advisorID) REFERENCES advisorProfile(advisorID) ON DELETE CASCADE,
  CONSTRAINT fkBridgeAdvisee  FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS terms (
  termID     INT AUTO_INCREMENT PRIMARY KEY,
  code       VARCHAR(32) NOT NULL UNIQUE,
  startDate  DATETIME NOT NULL,
  endDate    DATETIME NOT NULL,
  CONSTRAINT checkTerm CHECK (endDate > startDate)
);

CREATE TABLE IF NOT EXISTS courses (
  courseID    INT AUTO_INCREMENT PRIMARY KEY,
  courseName  VARCHAR(160) NOT NULL,
  description TEXT,
  credits     INT NOT NULL,
  CONSTRAINT checkCredits CHECK (credits > 0)
);

CREATE TABLE IF NOT EXISTS sections (
  sectionID      INT AUTO_INCREMENT PRIMARY KEY,
  courseID       INT NOT NULL,
  termID         INT NOT NULL,
  crn            VARCHAR(32) NOT NULL UNIQUE,
  capacity       INT NOT NULL,
  enrolled       INT NOT NULL DEFAULT 0,
  professorName  VARCHAR(160),
  status         ENUM('OPEN','CLOSED','CANCELLED') NOT NULL DEFAULT 'OPEN',
  description    TEXT,
  CONSTRAINT sectionCourses FOREIGN KEY (courseID) REFERENCES courses(courseID) ON DELETE RESTRICT,
  CONSTRAINT sectionTerm    FOREIGN KEY (termID)   REFERENCES terms(termID)     ON DELETE RESTRICT,
  CONSTRAINT enrolledCapacity CHECK (enrolled <= capacity)
);

CREATE TABLE IF NOT EXISTS schedules (
  scheduleID   INT AUTO_INCREMENT PRIMARY KEY,
  adviseeID    INT NOT NULL,
  termID       INT NOT NULL,
  source       ENUM('USER','ADVISOR','SYSTEM') NOT NULL DEFAULT 'USER',
  status       ENUM('DRAFT','APPROVED','REJECTED') NOT NULL DEFAULT 'DRAFT',
  createdWhen  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  approvedWhen DATETIME NULL,
  rejectedWhen DATETIME NULL,
  advisorFeedback VARCHAR(500) NULL,
  CONSTRAINT scheduleAdvisee FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID) ON DELETE CASCADE,
  CONSTRAINT scheduleTerm    FOREIGN KEY (termID)    REFERENCES terms(termID)           ON DELETE RESTRICT,
  CONSTRAINT scheduleDate CHECK (
    (approvedWhen IS NULL OR approvedWhen >= createdWhen) AND
    (rejectedWhen IS NULL OR rejectedWhen >= createdWhen)
  )
);

CREATE TABLE IF NOT EXISTS classes (
  classID      INT AUTO_INCREMENT PRIMARY KEY,
  sectionID    INT NOT NULL,
  scheduleID   INT NOT NULL,
  createdDate  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT classSection  FOREIGN KEY (sectionID)  REFERENCES sections(sectionID)   ON DELETE RESTRICT,
  CONSTRAINT classSchedule FOREIGN KEY (scheduleID) REFERENCES schedules(scheduleID) ON DELETE CASCADE,
  UNIQUE KEY uq_scheduleSection (scheduleID, sectionID)
);

CREATE TABLE IF NOT EXISTS enrollments (
  enrollmentID    INT AUTO_INCREMENT PRIMARY KEY,
  adviseeID       INT NOT NULL,
  sectionID       INT NOT NULL,
  courseID        INT NOT NULL,
  status          ENUM('ENROLLED','COMPLETED','DROPPED','WITHDRAWN') NOT NULL DEFAULT 'ENROLLED',
  grade           VARCHAR(8) NULL,
  creditsEarned   INT NOT NULL DEFAULT 0,
  attemptedNumber INT NOT NULL DEFAULT 1,
  createdWhen     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT enrolledAdvisee FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID) ON DELETE CASCADE,
  CONSTRAINT enrolledSection FOREIGN KEY (sectionID) REFERENCES sections(sectionID)       ON DELETE RESTRICT,
  CONSTRAINT enrolledCourse  FOREIGN KEY (courseID)  REFERENCES courses(courseID)         ON DELETE RESTRICT,
  UNIQUE KEY uq_enrollAdviseeSection (adviseeID, sectionID)
);

CREATE TABLE IF NOT EXISTS notifications (
  notificationID  INT AUTO_INCREMENT PRIMARY KEY,
  userID          INT NOT NULL,
  description     VARCHAR(500) NOT NULL,
  createdAt       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT notificationUser FOREIGN KEY (userID) REFERENCES users(userID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS degreePlan (
  degreePlanID  INT AUTO_INCREMENT PRIMARY KEY,
  adviseeID     INT NOT NULL,
  name          VARCHAR(120) NOT NULL,
  catalog       VARCHAR(20)  NOT NULL,
  status        ENUM('Draft','Active','Archived') NOT NULL DEFAULT 'Draft',
  createdWhen   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updatedWhen   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fkDegreePlanAdvisee FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID) ON DELETE CASCADE
);

-- ---------- Data ----------
INSERT INTO users (userID, username, email, role, isActive, createdDate) VALUES
(1, 'admin_01', 'admin1@college.edu', 'ADMIN', 1, '2024-11-10 08:30:00'),
(2, 'admin_02', 'admin2@college.edu', 'ADMIN', 1, '2025-01-15 09:00:00'),
(3, 'admin_03', 'admin3@college.edu', 'ADMIN', 1, '2025-02-20 10:15:00'),
(4, 'admin_04', 'admin4@college.edu', 'ADMIN', 1, '2025-03-05 12:00:00'),
(5, 'admin_05', 'admin5@college.edu', 'ADMIN', 1, '2025-03-22 14:00:00'),

(6, 'advisor_johnson', 'johnson@college.edu', 'ADVISOR', 1, '2024-12-03 10:30:00'),
(7, 'advisor_liu', 'liu@college.edu', 'ADVISOR', 1, '2024-12-10 09:45:00'),
(8, 'advisor_ramirez', 'ramirez@college.edu', 'ADVISOR', 1, '2025-01-07 14:15:00'),
(9, 'advisor_khan', 'khan@college.edu', 'ADVISOR', 1, '2025-01-18 08:00:00'),
(10, 'advisor_green', 'green@college.edu', 'ADVISOR', 1, '2025-02-02 13:00:00'),
(11, 'advisor_thomas', 'thomas@college.edu', 'ADVISOR', 1, '2025-02-20 11:45:00'),
(12, 'advisor_davis', 'davis@college.edu', 'ADVISOR', 1, '2025-03-05 09:30:00'),
(13, 'advisor_martin', 'martin@college.edu', 'ADVISOR', 1, '2025-03-21 10:10:00'),
(14, 'advisor_cho', 'cho@college.edu', 'ADVISOR', 1, '2025-04-11 15:20:00'),
(15, 'advisor_williams', 'williams@college.edu', 'ADVISOR', 1, '2025-04-30 12:40:00'),

(16, 'student_01', 's01@college.edu', 'STUDENT', 1, '2024-11-15 09:00:00'),
(17, 'student_02', 's02@college.edu', 'STUDENT', 1, '2024-11-17 09:10:00'),
(18, 'student_03', 's03@college.edu', 'STUDENT', 1, '2024-11-20 10:00:00'),
(19, 'student_04', 's04@college.edu', 'STUDENT', 1, '2024-11-25 10:45:00'),
(20, 'student_05', 's05@college.edu', 'STUDENT', 1, '2024-12-01 11:00:00'),
(21, 'student_06', 's06@college.edu', 'STUDENT', 1, '2024-12-07 11:30:00'),
(22, 'student_07', 's07@college.edu', 'STUDENT', 1, '2024-12-12 12:10:00'),
(23, 'student_08', 's08@college.edu', 'STUDENT', 1, '2024-12-19 14:00:00'),
(24, 'student_09', 's09@college.edu', 'STUDENT', 1, '2025-01-02 08:45:00'),
(25, 'student_10', 's10@college.edu', 'STUDENT', 1, '2025-01-07 09:20:00'),
(26, 'student_11', 's11@college.edu', 'STUDENT', 1, '2025-01-14 09:40:00'),
(27, 'student_12', 's12@college.edu', 'STUDENT', 1, '2025-01-20 10:10:00'),
(28, 'student_13', 's13@college.edu', 'STUDENT', 1, '2025-02-01 11:00:00'),
(29, 'student_14', 's14@college.edu', 'STUDENT', 1, '2025-02-10 11:45:00'),
(30, 'student_15', 's15@college.edu', 'STUDENT', 1, '2025-02-21 12:15:00'),
(31, 'student_16', 's16@college.edu', 'STUDENT', 1, '2025-03-03 13:00:00'),
(32, 'student_17', 's17@college.edu', 'STUDENT', 1, '2025-03-10 13:20:00'),
(33, 'student_18', 's18@college.edu', 'STUDENT', 1, '2025-03-17 14:00:00'),
(34, 'student_19', 's19@college.edu', 'STUDENT', 1, '2025-03-25 15:00:00'),
(35, 'student_20', 's20@college.edu', 'STUDENT', 1, '2025-04-01 08:30:00'),
(36, 'student_21', 's21@college.edu', 'STUDENT', 1, '2025-04-10 09:00:00'),
(37, 'student_22', 's22@college.edu', 'STUDENT', 1, '2025-04-20 09:15:00'),
(38, 'student_23', 's23@college.edu', 'STUDENT', 1, '2025-04-27 09:40:00'),
(39, 'student_24', 's24@college.edu', 'STUDENT', 1, '2025-05-02 10:10:00'),
(40, 'student_25', 's25@college.edu', 'STUDENT', 1, '2025-05-10 11:00:00');

-- Correct advisorProfile rows (match advisor userIDs 6–15)
INSERT INTO advisorProfile (advisorID, name, office, createdWhen) VALUES
(6,  'Dr. Johnson',  NULL, '2024-12-10 09:45:00'),
(7,  'Dr. Liu',      NULL, '2024-12-12 11:10:00'),
(8,  'Dr. Ramirez',  NULL, '2025-01-05 13:20:00'),
(9,  'Dr. Khan',     NULL, '2025-01-15 08:30:00'),
(10, 'Dr. Green',    NULL, '2025-02-03 10:45:00'),
(11, 'Dr. Thomas',   NULL, '2025-02-18 09:00:00'),
(12, 'Dr. Davis',    NULL, '2025-03-05 10:10:00'),
(13, 'Dr. Martin',   NULL, '2025-03-21 10:10:00'),
(14, 'Dr. Cho',      NULL, '2025-04-11 15:20:00'),
(15, 'Dr. Williams', NULL, '2025-04-30 12:40:00');

INSERT INTO adviseeProfile 
(adviseeID, userID, advisorID, major, degree_plan, classification, gpa, credits_completed, status, dateCreated, lastUpdated)
VALUES
(1, 16, 6, 'Computer Science', 'BS-CS', 'Freshman', 3.25, 30, 'Active', '2025-03-10 10:00:00', '2025-03-10 10:00:00'),
(2, 17, 6, 'Mathematics', 'BS-MATH', 'Sophomore', 3.40, 45, 'Active', '2025-03-11 10:00:00', '2025-03-11 10:00:00'),
(3, 18, 7, 'Information Systems', 'BS-IS', 'Junior', 3.10, 75, 'Active', '2025-03-12 10:00:00', '2025-03-12 10:00:00'),
(4, 19, 7, 'Mechanical Engineering', 'BS-ME', 'Senior', 2.95, 110, 'Active', '2025-03-13 10:00:00', '2025-03-13 10:00:00'),
(5, 20, 8, 'Civil Engineering', 'BS-CE', 'Senior', 3.50, 120, 'Graduated', '2025-03-14 10:00:00', '2025-03-14 10:00:00'),
(6, 21, 8, 'Electrical Engineering', 'BS-EE', 'Junior', 3.70, 80, 'Active', '2025-03-15 10:00:00', '2025-03-15 10:00:00'),
(7, 22, 9, 'Computer Engineering', 'BS-CPE', 'Sophomore', 3.45, 60, 'Active', '2025-03-16 10:00:00', '2025-03-16 10:00:00'),
(8, 23, 9, 'Business Administration', 'BBA', 'Freshman', 2.85, 25, 'Active', '2025-03-17 10:00:00', '2025-03-17 10:00:00'),
(9, 24, 10, 'Economics', 'BA-ECO', 'Junior', 3.55, 85, 'Active', '2025-03-18 10:00:00', '2025-03-18 10:00:00'),
(10,25, 10, 'Accounting', 'BS-ACC', 'Senior', 3.25, 110, 'Active', '2025-03-19 10:00:00', '2025-03-19 10:00:00'),
(11,26, 11, 'Finance', 'BBA-FIN', 'Freshman', 3.80, 20, 'Active', '2025-03-20 10:00:00', '2025-03-20 10:00:00'),
(12,27, 11, 'Marketing', 'BBA-MKT', 'Sophomore', 3.60, 50, 'Active', '2025-03-21 10:00:00', '2025-03-21 10:00:00'),
(13,28, 12, 'Psychology', 'BA-PSY', 'Junior', 3.15, 70, 'Active', '2025-03-22 10:00:00', '2025-03-22 10:00:00'),
(14,29, 12, 'Sociology', 'BA-SOC', 'Senior', 2.90, 105, 'Active', '2025-03-23 10:00:00', '2025-03-23 10:00:00'),
(15,30, 13, 'Political Science', 'BA-POL', 'Senior', 3.25, 115, 'Active', '2025-03-24 10:00:00', '2025-03-24 10:00:00'),
(16,31, 13, 'Philosophy', 'BA-PHI', 'Junior', 3.10, 75, 'Active', '2025-03-25 10:00:00', '2025-03-25 10:00:00'),
(17,32, 14, 'English Literature', 'BA-ENG', 'Sophomore', 3.35, 50, 'Active', '2025-03-26 10:00:00', '2025-03-26 10:00:00'),
(18,33, 14, 'History', 'BA-HIS', 'Senior', 3.00, 120, 'Graduated', '2025-03-27 10:00:00', '2025-03-27 10:00:00'),
(19,34, 15, 'Chemistry', 'BS-CHE', 'Junior', 3.55, 90, 'Active', '2025-03-28 10:00:00', '2025-03-28 10:00:00'),
(20,35, 15, 'Biology', 'BS-BIO', 'Sophomore', 3.75, 60, 'Active', '2025-03-29 10:00:00', '2025-03-29 10:00:00'),
(21,36, 6, 'Physics', 'BS-PHY', 'Senior', 3.40, 120, 'Graduated', '2025-03-30 10:00:00', '2025-03-30 10:00:00'),
(22,37, 7, 'Art History', 'BA-ART', 'Junior', 3.50, 90, 'Active', '2025-03-31 10:00:00', '2025-03-31 10:00:00'),
(23,38, 8, 'Architecture', 'BS-ARC', 'Freshman', 3.00, 25, 'Active', '2025-04-01 10:00:00', '2025-04-01 10:00:00'),
(24,39, 9, 'Music', 'BA-MUS', 'Sophomore', 3.25, 45, 'Active', '2025-04-02 10:00:00', '2025-04-02 10:00:00'),
(25,40,10, 'Nursing', 'BS-NUR', 'Freshman', 3.70, 15, 'Active', '2025-04-03 10:00:00', '2025-04-03 10:00:00');

INSERT INTO terms (termID, code, startDate, endDate) VALUES
(1, '2024FA', '2024-09-01 00:00:00', '2024-12-15 23:59:59'),
(2, '2025SP', '2025-01-10 00:00:00', '2025-05-01 23:59:59'),
(3, '2025SU', '2025-06-01 00:00:00', '2025-08-15 23:59:59');

INSERT INTO courses (courseID, courseName, description, credits) VALUES
(1, 'Introduction to Computer Science', 'Basic programming and computer science concepts', 3),
(2, 'Data Structures', 'Intermediate CS course on data structures', 3),
(3, 'Calculus I', 'Fundamental calculus concepts', 4),
(4, 'English Literature', 'Study of classical and modern literature', 3),
(5, 'Economics 101', 'Principles of micro and macroeconomics', 3),
(6, 'Physics I', 'Mechanics and motion', 4),
(7, 'Psychology', 'Introduction to psychology', 3),
(8, 'Sociology', 'Foundations of sociology', 3),
(9, 'Accounting I', 'Financial accounting principles', 3),
(10, 'Marketing', 'Introduction to marketing', 3);

-- Correct table name here: sections (not section)
INSERT INTO sections (sectionID, courseID, termID, crn, capacity, enrolled, professorName, status, description) VALUES
(1, 1, 2, 'CS101-SP', 30, 25, 'Dr. Alan Turing', 'OPEN', 'Introductory CS course'),
(2, 2, 2, 'CS201-SP', 25, 20, 'Dr. Grace Hopper', 'OPEN', 'Intermediate CS course'),
(3, 3, 2, 'MATH101-SP', 40, 38, 'Dr. Isaac Newton', 'OPEN', 'Calculus I'),
(4, 4, 2, 'ENG201-SP', 35, 33, 'Dr. Jane Austen', 'OPEN', 'English Literature survey'),
(5, 5, 2, 'ECO101-SP', 50, 48, 'Dr. Adam Smith', 'OPEN', 'Economics principles'),
(6, 6, 2, 'PHY101-SP', 40, 37, 'Dr. Albert Einstein', 'OPEN', 'Physics mechanics'),
(7, 7, 2, 'PSY101-SP', 35, 30, 'Dr. Sigmund Freud', 'OPEN', 'Intro to Psychology'),
(8, 8, 2, 'SOC101-SP', 35, 32, 'Dr. Emile Durkheim', 'OPEN', 'Sociology basics'),
(9, 9, 2, 'ACC101-SP', 30, 28, 'Dr. Luca Pacioli', 'OPEN', 'Accounting principles'),
(10,10, 2, 'MKT101-SP', 30, 27, 'Dr. Philip Kotler', 'OPEN', 'Introduction to Marketing'),
(11,1,3,'CS101-SU', 30, 10, 'Dr. Alan Turing', 'OPEN', 'Summer CS intro'),
(12,3,3,'MATH101-SU', 40, 25, 'Dr. Isaac Newton', 'OPEN', 'Summer Calculus'),
(13,4,3,'ENG201-SU', 35, 20, 'Dr. Jane Austen', 'OPEN', 'Summer Literature'),
(14,6,3,'PHY101-SU', 40, 15, 'Dr. Albert Einstein', 'OPEN', 'Summer Physics'),
(15,2,3,'CS201-SU', 25, 12, 'Dr. Grace Hopper', 'OPEN', 'Summer Data Structures');

-- Map adviseeIDs correctly (1–25) and source enum to SYSTEM
INSERT INTO schedules (scheduleID, adviseeID, termID, source, status, createdWhen, approvedWhen, rejectedWhen, advisorFeedback) VALUES
(1,  1,  2, 'SYSTEM', 'APPROVED', '2025-01-05 09:00:00', '2025-01-06 10:00:00', NULL, 'Reviewed and approved. Great selection of courses.'),
(2,  2,  2, 'SYSTEM', 'APPROVED', '2025-01-06 09:00:00', '2025-01-07 10:00:00', NULL, 'Approved – keep an eye on workload balance.'),
(3,  3,  2, 'SYSTEM', 'APPROVED', '2025-01-07 09:00:00', '2025-01-08 10:00:00', NULL, 'Approved after verifying prerequisites.'),
(4,  4,  2, 'SYSTEM', 'APPROVED', '2025-01-08 09:00:00', '2025-01-09 10:00:00', NULL, 'Approved. Remember to confirm lab times.'),
(5,  5,  2, 'SYSTEM', 'APPROVED', '2025-01-09 09:00:00', '2025-01-10 10:00:00', NULL, 'Approved and ready for registration.'),
(6,  6,  2, 'SYSTEM', 'DRAFT',    '2025-01-10 09:00:00', NULL, NULL, NULL),
(7,  7,  2, 'SYSTEM', 'DRAFT',    '2025-01-11 09:00:00', NULL, NULL, NULL),
(8,  8,  2, 'SYSTEM', 'APPROVED', '2025-01-12 09:00:00', '2025-01-13 10:00:00', NULL, 'Approved. Nice mix of core and electives.'),
(9,  9,  2, 'SYSTEM', 'APPROVED', '2025-01-13 09:00:00', '2025-01-14 10:00:00', NULL, 'Approved. Stay on top of project deadlines.'),
(10, 10, 2, 'SYSTEM', 'APPROVED', '2025-01-14 09:00:00', '2025-01-15 10:00:00', NULL, 'Approved with no changes.'),
(11, 11, 2, 'SYSTEM', 'DRAFT',    '2025-01-15 09:00:00', NULL, NULL, NULL),
(12, 12, 2, 'SYSTEM', 'DRAFT',    '2025-01-16 09:00:00', NULL, NULL, NULL),
(13, 13, 2, 'SYSTEM', 'APPROVED', '2025-01-17 09:00:00', '2025-01-18 10:00:00', NULL, 'Approved. Honors seminar confirmed.'),
(14, 14, 2, 'SYSTEM', 'APPROVED', '2025-01-18 09:00:00', '2025-01-19 10:00:00', NULL, 'Approved – good capstone alignment.'),
(15, 15, 2, 'SYSTEM', 'APPROVED', '2025-01-19 09:00:00', '2025-01-20 10:00:00', NULL, 'Approved pending book purchases.'),
(16, 16, 2, 'SYSTEM', 'DRAFT',    '2025-01-20 09:00:00', NULL, NULL, NULL),
(17, 17, 2, 'SYSTEM', 'DRAFT',    '2025-01-21 09:00:00', NULL, NULL, NULL),
(18, 18, 2, 'SYSTEM', 'APPROVED', '2025-01-22 09:00:00', '2025-01-23 10:00:00', NULL, 'Approved. Internship credit verified.'),
(19, 19, 2, 'SYSTEM', 'APPROVED', '2025-01-23 09:00:00', '2025-01-24 10:00:00', NULL, 'Approved. Keep Fridays free for research hours.'),
(20, 20, 2, 'SYSTEM', 'APPROVED', '2025-01-24 09:00:00', '2025-01-25 10:00:00', NULL, 'Approved – graduation requirements satisfied.'),
(21, 21, 2, 'SYSTEM', 'DRAFT',    '2025-01-25 09:00:00', NULL, NULL, NULL),
(22, 22, 2, 'SYSTEM', 'DRAFT',    '2025-01-26 09:00:00', NULL, NULL, NULL),
(23, 23, 2, 'SYSTEM', 'APPROVED', '2025-01-27 09:00:00', '2025-01-28 10:00:00', NULL, 'Approved – study abroad prerequisites satisfied.'),
(24, 24, 2, 'SYSTEM', 'APPROVED', '2025-01-28 09:00:00', '2025-01-29 10:00:00', NULL, 'Approved with encouragement to add tutoring hours.'),
(25, 25, 2, 'SYSTEM', 'APPROVED', '2025-01-29 09:00:00', '2025-01-30 10:00:00', NULL, 'Approved. Nice work staying ahead.');

INSERT INTO classes (classID, sectionID, scheduleID, createdDate) VALUES
(1, 1, 1,  '2025-01-05 09:05:00'),
(2, 3, 1,  '2025-01-05 09:05:00'),
(3, 4, 2,  '2025-01-06 09:05:00'),
(4, 5, 3,  '2025-01-07 09:05:00'),
(5, 2, 4,  '2025-01-08 09:05:00'),
(6, 6, 5,  '2025-01-09 09:05:00'),
(7, 7, 8,  '2025-01-12 09:05:00'),
(8, 8, 9,  '2025-01-13 09:05:00'),
(9, 9, 10, '2025-01-14 09:05:00'),
(10,10,10, '2025-01-14 09:05:00');

-- Map adviseeIDs 16..25 -> 1..10
INSERT INTO enrollments (enrollmentID, adviseeID, sectionID, courseID, status, grade, creditsEarned, attemptedNumber, createdWhen) VALUES
(1,  1, 1, 1, 'ENROLLED', 'A',  3, 1, '2025-01-05 09:10:00'),
(2,  1, 3, 3, 'ENROLLED', 'B+', 4, 1, '2025-01-05 09:12:00'),
(3,  2, 1, 1, 'ENROLLED', 'A-', 3, 1, '2025-01-06 09:10:00'),
(4,  2, 2, 2, 'ENROLLED', 'B',  3, 1, '2025-01-06 09:12:00'),
(5,  3, 4, 4, 'ENROLLED', 'B+', 3, 1, '2025-01-07 09:15:00'),
(6,  3, 5, 5, 'ENROLLED', 'A',  3, 1, '2025-01-07 09:17:00'),
(7,  4, 2, 2, 'ENROLLED', 'C+', 3, 1, '2025-01-08 09:10:00'),
(8,  4, 6, 6, 'ENROLLED', 'B',  4, 1, '2025-01-08 09:12:00'),
(9,  5, 7, 7, 'ENROLLED', 'A',  3, 1, '2025-01-09 09:10:00'),
(10, 5, 8, 8, 'ENROLLED', 'A-', 3, 1, '2025-01-09 09:12:00'),
(11, 6, 1, 1, 'ENROLLED', NULL, 0, 1, '2025-01-10 09:10:00'),
(12, 6, 3, 3, 'ENROLLED', NULL, 0, 1, '2025-01-10 09:12:00'),
(13, 7, 4, 4, 'ENROLLED', NULL, 0, 1, '2025-01-11 09:10:00'),
(14, 7, 5, 5, 'ENROLLED', NULL, 0, 1, '2025-01-11 09:12:00'),
(15, 8, 6, 6, 'ENROLLED', 'B+', 4, 1, '2025-01-12 09:10:00'),
(16, 8, 7, 7, 'ENROLLED', 'A',  3, 1, '2025-01-12 09:12:00'),
(17, 9, 8, 8, 'ENROLLED', 'A-', 3, 1, '2025-01-13 09:10:00'),
(18, 9, 9, 9, 'ENROLLED', 'B+', 3, 1, '2025-01-13 09:12:00'),
(19,10,10,10,'ENROLLED', 'B',  3, 1, '2025-01-14 09:10:00'),
(20,10,2, 2, 'ENROLLED', 'A-', 3, 1, '2025-01-14 09:12:00');

-- Use correct enum casing for status ('Active')
INSERT INTO degreePlan (degreePlanID, adviseeID, name, catalog, status, createdWhen, updatedWhen) VALUES
(1,  1, 'BS Computer Science',        'CAT2024', 'Active', '2025-01-05 09:00:00', '2025-01-05 09:00:00'),
(2,  2, 'BS Computer Science',        'CAT2024', 'Active', '2025-01-06 09:00:00', '2025-01-06 09:00:00'),
(3,  3, 'BBA Business Administration','CAT2024', 'Active', '2025-01-07 09:00:00', '2025-01-07 09:00:00'),
(4,  4, 'BS Physics',                 'CAT2024', 'Active', '2025-01-08 09:00:00', '2025-01-08 09:00:00'),
(5,  5, 'BA Psychology',              'CAT2024', 'Active', '2025-01-09 09:00:00', '2025-01-09 09:00:00'),
(6,  6, 'BS Computer Science',        'CAT2024', 'Draft',  '2025-01-10 09:00:00', '2025-01-10 09:00:00'),
(7,  7, 'BBA Business Administration','CAT2024', 'Draft',  '2025-01-11 09:00:00', '2025-01-11 09:00:00'),
(8,  8, 'BS Physics',                 'CAT2024', 'Active', '2025-01-12 09:00:00', '2025-01-12 09:00:00'),
(9,  9, 'BA Psychology',              'CAT2024', 'Active', '2025-01-13 09:00:00', '2025-01-13 09:00:00'),
(10,10, 'BBA Marketing',              'CAT2024', 'Active', '2025-01-14 09:00:00', '2025-01-14 09:00:00');

INSERT INTO notifications (notificationID, userID, description, createdAt) VALUES
(1, 16, 'Your schedule for Spring 2025 has been approved.', '2025-01-06 10:05:00'),
(2, 17, 'Your schedule for Spring 2025 has been approved.', '2025-01-07 10:05:00'),
(3, 18, 'Your schedule for Spring 2025 has been approved.', '2025-01-08 10:05:00'),
(4, 19, 'Your schedule for Spring 2025 has been approved.', '2025-01-09 10:05:00'),
(5, 20, 'Your schedule for Spring 2025 has been approved.', '2025-01-10 10:05:00'),
(6, 21, 'Draft schedule created. Please review before submission.', '2025-01-10 10:15:00'),
(7, 22, 'Draft schedule created. Please review before submission.', '2025-01-11 10:15:00'),
(8, 23, 'Your schedule for Spring 2025 has been approved.', '2025-01-12 10:05:00'),
(9, 24, 'Your schedule for Spring 2025 has been approved.', '2025-01-13 10:05:00'),
(10,25, 'Your schedule for Spring 2025 has been approved.', '2025-01-14 10:05:00');

CREATE TABLE IF NOT EXISTS degree_requirement_sets (
  requirementSetID INT AUTO_INCREMENT PRIMARY KEY,
  programCode      VARCHAR(64) NOT NULL,
  catalogYear      VARCHAR(32) NOT NULL,
  programName      VARCHAR(255) NOT NULL,
  totalCredits     INT NOT NULL DEFAULT 120,
  requirementData  JSON NOT NULL,
  sourceDocument   VARCHAR(255),
  createdAt        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updatedAt        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_program_catalog (programCode, catalogYear)
);

CREATE TABLE IF NOT EXISTS advisee_degree_context (
  contextID        INT AUTO_INCREMENT PRIMARY KEY,
  adviseeID        INT NOT NULL UNIQUE,
  requirementSetID INT NOT NULL,
  completedCourses JSON NOT NULL,
  overrides        JSON NULL,
  notes            TEXT NULL,
  createdAt        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updatedAt        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_context_requirement FOREIGN KEY (requirementSetID) REFERENCES degree_requirement_sets(requirementSetID)
);

CREATE TABLE IF NOT EXISTS degree_plan_validations (
  validationID      INT AUTO_INCREMENT PRIMARY KEY,
  adviseeID         INT NOT NULL,
  contextID         INT NULL,
  requirementSetID  INT NULL,
  status            ENUM('PENDING','RUNNING','PASSED','FAILED','ERROR') NOT NULL DEFAULT 'PENDING',
  runType           ENUM('MANUAL','AUTOMATIC') NOT NULL DEFAULT 'MANUAL',
  completionPercent DECIMAL(5,2) NOT NULL DEFAULT 0,
  issues            JSON NULL,
  message           VARCHAR(255),
  triggeredBy       INT NULL,
  startedAt         DATETIME NULL,
  finishedAt        DATETIME NULL,
  createdAt         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updatedAt         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_validation_context FOREIGN KEY (contextID) REFERENCES advisee_degree_context(contextID),
  CONSTRAINT fk_validation_requirement FOREIGN KEY (requirementSetID) REFERENCES degree_requirement_sets(requirementSetID),
  INDEX idx_validation_advisee (adviseeID)
);

CREATE TABLE IF NOT EXISTS advisee_requirements (
  adviseeID INT PRIMARY KEY,
  requirementSetID INT NOT NULL,
  FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID) ON DELETE CASCADE,
  FOREIGN KEY (requirementSetID) REFERENCES degree_requirement_sets(requirementSetID) ON DELETE CASCADE
);

-- ------------------------------------------------------
-- Sample Degree Plan Requirement Sets + Contexts
-- ------------------------------------------------------

INSERT INTO degree_requirement_sets
  (requirementSetID, programCode, catalogYear, programName, totalCredits, requirementData, sourceDocument, createdAt, updatedAt)
VALUES
  (101, 'BS-CS', 'CAT2024', 'B.S. Computer Science', 120,
    '[{"id":"core","title":"Core Curriculum","requiredCredits":36,"courses":[{"code":"ENG 1013","title":"Composition I","credits":3},{"code":"MATH 2804","title":"Calculus I","credits":4},{"code":"CS 1013","title":"Intro to Programming","credits":3},{"code":"CS 2023","title":"Data Structures","credits":3}]},{"id":"advanced","title":"Advanced Major Requirements","requiredCredits":24,"courses":[{"code":"CS 3013","title":"Algorithms","credits":3},{"code":"CS 3223","title":"Operating Systems","credits":3},{"code":"CS 3413","title":"Database Systems","credits":3},{"code":"CS 4XX3","title":"Upper-Level Elective","credits":3}]}]'
  , 'https://adviseme.example.edu/bs-cs', '2025-03-20 09:00:00', '2025-03-20 09:00:00'),
  (102, 'BS-MATH', 'CAT2023', 'B.S. Mathematics', 120,
    '[{"id":"foundation","title":"Foundational Math","requiredCredits":30,"courses":[{"code":"MATH 1603","title":"Trig","credits":3},{"code":"MATH 2004","title":"Calculus II","credits":4},{"code":"STAT 2503","title":"Statistics","credits":3}]},{"id":"major","title":"Upper-Level Math","requiredCredits":24,"courses":[{"code":"MATH 3103","title":"Linear Algebra","credits":3},{"code":"MATH 3303","title":"Abstract Algebra","credits":3},{"code":"MATH 3403","title":"Real Analysis","credits":3}]}]'
  , 'https://adviseme.example.edu/bs-math', '2025-03-20 09:10:00', '2025-03-20 09:10:00'),
  (103, 'BS-IS', 'CAT2022', 'B.S. Information Systems', 120,
    '[{"id":"core","title":"Business Core","requiredCredits":30,"courses":[{"code":"ACCT 2003","title":"Accounting","credits":3},{"code":"ECON 2103","title":"Economics","credits":3}]},{"id":"technology","title":"Technology Core","requiredCredits":30,"courses":[{"code":"IS 2003","title":"Systems Analysis","credits":3},{"code":"IS 3203","title":"Enterprise Architecture","credits":3}]}]'
  , 'https://adviseme.example.edu/bs-is', '2025-03-20 09:20:00', '2025-03-20 09:20:00');

INSERT INTO advisee_degree_context
  (contextID, adviseeID, requirementSetID, completedCourses, overrides, notes, createdAt, updatedAt)
VALUES
  (201, 1, 101,
    '[{"code":"ENG 1013","title":"Composition I","credits":3,"term":"Fall 2023","status":"COMPLETED"},{"code":"MATH 2804","title":"Calculus I","credits":4,"term":"Fall 2023","status":"COMPLETED"},{"code":"CS 1013","title":"Intro to Programming","credits":3,"term":"Fall 2023","status":"COMPLETED"}]',
    NULL,
    'Seeded from degree audit import.',
    '2025-03-21 08:30:00', '2025-03-21 08:30:00'),
  (202, 2, 102,
    '[{"code":"MATH 1603","title":"Trigonometry","credits":3,"term":"Fall 2023","status":"COMPLETED"},{"code":"MATH 2004","title":"Calculus II","credits":4,"term":"Spring 2024","status":"IN_PROGRESS"}]',
    NULL,
    'Advisor-entered coursework snapshot.',
    '2025-03-21 08:45:00', '2025-03-21 08:45:00'),
  (203, 3, 103,
    '[{"code":"ACCT 2003","title":"Accounting","credits":3,"term":"Fall 2023","status":"COMPLETED"},{"code":"ECON 2103","title":"Economics","credits":3,"term":"Fall 2023","status":"COMPLETED"},{"code":"IS 2003","title":"Systems Analysis","credits":3,"term":"Spring 2024","status":"COMPLETED"}]',
    NULL,
    'Imported from PDF scrape demo.',
    '2025-03-21 09:00:00', '2025-03-21 09:00:00');

INSERT INTO degree_plan_validations
  (validationID, adviseeID, contextID, requirementSetID, status, runType, completionPercent, issues, message, triggeredBy, startedAt, finishedAt, createdAt, updatedAt)
VALUES
  (301, 1, 201, 101, 'PASSED', 'AUTOMATIC', 62.5,
    '[]',
    'Auto validation succeeded after PDF import.',
    6,
    '2025-03-21 08:31:00', '2025-03-21 08:31:30', '2025-03-21 08:31:00', '2025-03-21 08:31:30'),
  (302, 2, 202, 102, 'FAILED', 'AUTOMATIC', 35.0,
    '[{"requirementId":"foundation","message":"Missing foundational courses","missingCourses":["STAT 2503"]}]',
    'Needs additional foundational math work.',
    7,
    '2025-03-21 08:46:00', '2025-03-21 08:47:10', '2025-03-21 08:46:00', '2025-03-21 08:47:10'),
  (303, 3, 203, 103, 'RUNNING', 'MANUAL', 50.0,
    '[]',
    'Manual validation currently running.',
    8,
    '2025-03-21 09:01:00', NULL, '2025-03-21 09:01:00', '2025-03-21 09:01:00');

INSERT INTO advisee_requirements (adviseeID, requirementSetID) VALUES
  (1, 101),
  (2, 102),
  (3, 103)
ON DUPLICATE KEY UPDATE requirementSetID = VALUES(requirementSetID);
