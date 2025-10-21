create table if not exists users ( 
    userID      INT PRIMARY KEY,
    username    VARCHAR(100) NOT NULL UNIQUE,
    email       VARCHAR(255) NOT NULL UNIQUE,
    role        VARCHAR(32) NOT NULL,
    isActive    INT,
    createdDate DATETIME,
    CONSTRAINT checkRoles CHECK (role IN ('STUDENT', 'ADVISOR', 'ADMIN'))
)

create table if not exists advisorProfile (
    degreePlanID    INT PRIMARY KEY,
    adviseeID       INT NOT NULL,
    name            VARCHAR(160) NOT NULL,
    catalog         VARCHAR(32),
    status          VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    createdWhen     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT degreePlanAdvisee FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID)
)

create table if not exists terms (
    termID      INT PRIMARY KEY 
    code        VARCHAR(32) NOT NULL,
    startDate   DATETIME NOT NULL,
    endDate     DATETIME NOT NULL,
    CONSTRAINT  checkTerm CHECK (endDate > startDate)
)

create time if not exists courses (
    courseID        INT PRIMARY KEY,
    courseName      VARCHAR(160) NOT NULL,
    description     TEXT,
    credits         INT NOT NULL,
    CONSTRAINT checkCredits CHECK (credits > 0)
)

create table if not exists section (
    sectionID       INT PRIMARY KEY,
    courseID        INT NOT NULL,
    termID          INT NOT NULL,
    crn             VARCHAR(32) NOT NULL UNIQUE,
    capacity        INT NOT NULL,
    enrolled        INT NOT NULL DEFAULT 0,
    professorName   VARCHAR(160).
    status          VARCHAR(32) NOT NULL DEFAULT 'OPEN'
    description     TEXT,
    CONSTRAINT sectionCourses FOREIGN KEY (courseID) REFERENCES course(courseID)
    CONSTRAINT sectionTerm FOREIGN KEY (termID) REFERENCES terms(termID)
    CONSTRAINT enrolledCapacity CHECK (enrolled <= capacity) 
)

create table if not exists schedules (
    scheduleID      INT PRIMARY KEY, 
    adviseeID       INT NOT NULL,
    termID          INT NOT NULL,
    source          VARCHAR(32) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
    createdWhen     DATETIME NOT DEFAULT CURRENT_TIMESTAMP,
    approvedWhen    DATETIME,
    rejectedWhen    DATETIME,
    CONSTRAINT scheduleAdvisee FOREIGN KEY (adviseeID) REFERENCES adviseeProfile (adviseeID)
    CONSTRAINT scheduleTerm FOREIGN KEY (termID) REFERENCES terms(termID)
    CONSTRAINT scheduleDate CHECK (
        (approvedWhen IS NULL OR approvedWhen >= createdWhen) AND 
        (rejectedWhen IS NULL OR rejectedWhen >= createdWhen)
    )
)

create table is not exists classes (
    classID     INT PRIMARY KEY, 
    sectionID   INT NOT NULL,
    scheduleID  INT NOT NULL,
    createdDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT classSection FOREIGN KEY (sectionID) REFERENCES sections(sectionID)
    CONSTRAINT classSchedule FOREIGN KEY (scheduleID) REFERENCES schedule(scheduleID)
    UNIQUE KEY scheduleSection(scheduleID, sectionID)
)

create table if not exists enrollments (
    enrollmentID    INT PRIMARY KEY, 
    adviseeID       INT NOT NULL,
    sectionID       INT NOT NULL,
    courseID        INT NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'ENROLLED',
    grade           VARCHAR(8),
    creditsEarned   INT NOT NULL,
    attemptedNumber INT NOT NULL,
    createdWhen     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT enrolledAdvisee FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(sectionID)
    CONSTRAINT enrolledSection FOREIGN KEY (sectionID) REFERENCES sections(sectionID)
    CONSTRAINT enrolledCourse  FOREIGN KEY (courseID) REFERENCES  courses(courseID)
    CONSTRAINT enrollAdviseeSection UNIQUE (adviseeID, sectionID)
)

create table if not exists notifications (
    notificationID  INT PRIMARY KEY,
    userID          INT NOT NULL,
    description     VARCHAR(500) NOT NULL,
    createdAt       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT notificationUser FOREIGN KEY (userID) REFERENCES user(userID)
)

-- Data
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

INSERT INTO advisorProfile (degreePlanID, adviseeID, name, catalog, status, createdWhen) VALUES
(1, 0, 'Dr. Johnson', 'CAT2024', 'ACTIVE', '2024-12-10 09:45:00'),
(2, 0, 'Dr. Liu', 'CAT2024', 'ACTIVE', '2024-12-12 11:10:00'),
(3, 0, 'Dr. Ramirez', 'CAT2024', 'ACTIVE', '2025-01-05 13:20:00'),
(4, 0, 'Dr. Khan', 'CAT2024', 'ACTIVE', '2025-01-15 08:30:00'),
(5, 0, 'Dr. Green', 'CAT2024', 'ACTIVE', '2025-02-03 10:45:00'),
(6, 0, 'Dr. Thomas', 'CAT2024', 'ACTIVE', '2025-02-18 09:00:00'),
(7, 0, 'Dr. Davis', 'CAT2024', 'ACTIVE', '2025-03-05 10:10:00'),
(8, 0, 'Dr. Martin', 'CAT2024', 'ACTIVE', '2025-03-21 10:10:00'),
(9, 0, 'Dr. Cho', 'CAT2024', 'ACTIVE', '2025-04-11 15:20:00'),
(10, 0, 'Dr. Williams', 'CAT2024', 'ACTIVE', '2025-04-30 12:40:00');

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

INSERT INTO section (sectionID, courseID, termID, crn, capacity, enrolled, professorName, status, description) VALUES
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

INSERT INTO schedules (scheduleID, adviseeID, termID, source, status, createdWhen, approvedWhen, rejectedWhen) VALUES
(1, 16, 2, 'AUTOGEN', 'APPROVED', '2025-01-05 09:00:00', '2025-01-06 10:00:00', NULL),
(2, 17, 2, 'AUTOGEN', 'APPROVED', '2025-01-06 09:00:00', '2025-01-07 10:00:00', NULL),
(3, 18, 2, 'AUTOGEN', 'APPROVED', '2025-01-07 09:00:00', '2025-01-08 10:00:00', NULL),
(4, 19, 2, 'AUTOGEN', 'APPROVED', '2025-01-08 09:00:00', '2025-01-09 10:00:00', NULL),
(5, 20, 2, 'AUTOGEN', 'APPROVED', '2025-01-09 09:00:00', '2025-01-10 10:00:00', NULL),
(6, 21, 2, 'AUTOGEN', 'DRAFT',    '2025-01-10 09:00:00', NULL, NULL),
(7, 22, 2, 'AUTOGEN', 'DRAFT',    '2025-01-11 09:00:00', NULL, NULL),
(8, 23, 2, 'AUTOGEN', 'APPROVED', '2025-01-12 09:00:00', '2025-01-13 10:00:00', NULL),
(9, 24, 2, 'AUTOGEN', 'APPROVED', '2025-01-13 09:00:00', '2025-01-14 10:00:00', NULL),
(10,25, 2, 'AUTOGEN', 'APPROVED', '2025-01-14 09:00:00', '2025-01-15 10:00:00', NULL),
(11,26,2, 'AUTOGEN', 'DRAFT',    '2025-01-15 09:00:00', NULL, NULL),
(12,27,2, 'AUTOGEN', 'DRAFT',    '2025-01-16 09:00:00', NULL, NULL),
(13,28,2, 'AUTOGEN', 'APPROVED', '2025-01-17 09:00:00', '2025-01-18 10:00:00', NULL),
(14,29,2, 'AUTOGEN', 'APPROVED', '2025-01-18 09:00:00', '2025-01-19 10:00:00', NULL),
(15,30,2, 'AUTOGEN', 'APPROVED', '2025-01-19 09:00:00', '2025-01-20 10:00:00', NULL),
(16,31,2, 'AUTOGEN', 'DRAFT',    '2025-01-20 09:00:00', NULL, NULL),
(17,32,2, 'AUTOGEN', 'DRAFT',    '2025-01-21 09:00:00', NULL, NULL),
(18,33,2, 'AUTOGEN', 'APPROVED', '2025-01-22 09:00:00', '2025-01-23 10:00:00', NULL),
(19,34,2, 'AUTOGEN', 'APPROVED', '2025-01-23 09:00:00', '2025-01-24 10:00:00', NULL),
(20,35,2, 'AUTOGEN', 'APPROVED', '2025-01-24 09:00:00', '2025-01-25 10:00:00', NULL),
(21,36,2, 'AUTOGEN', 'DRAFT',    '2025-01-25 09:00:00', NULL, NULL),
(22,37,2, 'AUTOGEN', 'DRAFT',    '2025-01-26 09:00:00', NULL, NULL),
(23,38,2, 'AUTOGEN', 'APPROVED', '2025-01-27 09:00:00', '2025-01-28 10:00:00', NULL),
(24,39,2, 'AUTOGEN', 'APPROVED', '2025-01-28 09:00:00', '2025-01-29 10:00:00', NULL),
(25,40,2, 'AUTOGEN', 'APPROVED', '2025-01-29 09:00:00', '2025-01-30 10:00:00', NULL);

INSERT INTO classes (classID, sectionID, scheduleID, createdDate) VALUES
(1, 1, 1, '2025-01-05 09:05:00'),
(2, 3, 1, '2025-01-05 09:05:00'),
(3, 4, 2, '2025-01-06 09:05:00'),
(4, 5, 3, '2025-01-07 09:05:00'),
(5, 2, 4, '2025-01-08 09:05:00'),
(6, 6, 5, '2025-01-09 09:05:00'),
(7, 7, 8, '2025-01-12 09:05:00'),
(8, 8, 9, '2025-01-13 09:05:00'),
(9, 9, 10, '2025-01-14 09:05:00'),
(10,10,10, '2025-01-14 09:05:00');

INSERT INTO enrollments (enrollmentID, adviseeID, sectionID, courseID, status, grade, creditsEarned, attemptedNumber, createdWhen) VALUES
(1, 16, 1, 1, 'ENROLLED', 'A', 3, 1, '2025-01-05 09:10:00'),
(2, 16, 3, 3, 'ENROLLED', 'B+', 4, 1, '2025-01-05 09:12:00'),
(3, 17, 1, 1, 'ENROLLED', 'A-', 3, 1, '2025-01-06 09:10:00'),
(4, 17, 2, 2, 'ENROLLED', 'B', 3, 1, '2025-01-06 09:12:00'),
(5, 18, 4, 4, 'ENROLLED', 'B+', 3, 1, '2025-01-07 09:15:00'),
(6, 18, 5, 5, 'ENROLLED', 'A', 3, 1, '2025-01-07 09:17:00'),
(7, 19, 2, 2, 'ENROLLED', 'C+', 3, 1, '2025-01-08 09:10:00'),
(8, 19, 6, 6, 'ENROLLED', 'B', 4, 1, '2025-01-08 09:12:00'),
(9, 20, 7, 7, 'ENROLLED', 'A', 3, 1, '2025-01-09 09:10:00'),
(10, 20, 8, 8, 'ENROLLED', 'A-', 3, 1, '2025-01-09 09:12:00'),
(11, 21, 1, 1, 'ENROLLED', NULL, 0, 1, '2025-01-10 09:10:00'),
(12, 21, 3, 3, 'ENROLLED', NULL, 0, 1, '2025-01-10 09:12:00'),
(13, 22, 4, 4, 'ENROLLED', NULL, 0, 1, '2025-01-11 09:10:00'),
(14, 22, 5, 5, 'ENROLLED', NULL, 0, 1, '2025-01-11 09:12:00'),
(15, 23, 6, 6, 'ENROLLED', 'B+', 4, 1, '2025-01-12 09:10:00'),
(16, 23, 7, 7, 'ENROLLED', 'A', 3, 1, '2025-01-12 09:12:00'),
(17, 24, 8, 8, 'ENROLLED', 'A-', 3, 1, '2025-01-13 09:10:00'),
(18, 24, 9, 9, 'ENROLLED', 'B+', 3, 1, '2025-01-13 09:12:00'),
(19, 25, 10, 10, 'ENROLLED', 'B', 3, 1, '2025-01-14 09:10:00'),
(20, 25, 2, 2, 'ENROLLED', 'A-', 3, 1, '2025-01-14 09:12:00');

INSERT INTO degreePlan (degreePlanID, adviseeID, name, catalog, status, createdWhen, updatedWhen) VALUES
(1, 16, 'BS Computer Science', 'CAT2024', 'ACTIVE', '2025-01-05 09:00:00', '2025-01-05 09:00:00'),
(2, 17, 'BS Computer Science', 'CAT2024', 'ACTIVE', '2025-01-06 09:00:00', '2025-01-06 09:00:00'),
(3, 18, 'BBA Business Administration', 'CAT2024', 'ACTIVE', '2025-01-07 09:00:00', '2025-01-07 09:00:00'),
(4, 19, 'BS Physics', 'CAT2024', 'ACTIVE', '2025-01-08 09:00:00', '2025-01-08 09:00:00'),
(5, 20, 'BA Psychology', 'CAT2024', 'ACTIVE', '2025-01-09 09:00:00', '2025-01-09 09:00:00'),
(6, 21, 'BS Computer Science', 'CAT2024', 'DRAFT', '2025-01-10 09:00:00', '2025-01-10 09:00:00'),
(7, 22, 'BBA Business Administration', 'CAT2024', 'DRAFT', '2025-01-11 09:00:00', '2025-01-11 09:00:00'),
(8, 23, 'BS Physics', 'CAT2024', 'ACTIVE', '2025-01-12 09:00:00', '2025-01-12 09:00:00'),
(9, 24, 'BA Psychology', 'CAT2024', 'ACTIVE', '2025-01-13 09:00:00', '2025-01-13 09:00:00'),
(10,25, 'BBA Marketing', 'CAT2024', 'ACTIVE', '2025-01-14 09:00:00', '2025-01-14 09:00:00');

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
