CREATE TABLE IF NOT EXISTS users (
    userID      INT PRIMARY KEY,
    username    VARCHAR(100) NOT NULL UNIQUE,
    email       VARCHAR(255) NOT NULL UNIQUE,
    role        ENUM('STUDENT', 'ADVISOR', 'ADMIN') NOT NULL,
    isActive    TINYINT,
    createdDate DATETIME
);

CREATE TABLE IF NOT EXISTS adviseeProfile (
    adviseeID         INT AUTO_INCREMENT PRIMARY KEY,
    userID            INT NOT NULL,              
    advisorID         INT NOT NULL,            
    major             VARCHAR(100) NOT NULL,
    degree_plan       VARCHAR(100),
    classification    ENUM('Freshman', 'Sophomore', 'Junior', 'Senior') NOT NULL,
    gpa               DECIMAL(3,2),
    credits_completed INT DEFAULT 0,
    status            ENUM('Active', 'Inactive', 'Graduated', 'Suspended') DEFAULT 'Active',
    dateCreated       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lastUpdated       TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_advisee_user FOREIGN KEY (userID)
        REFERENCES users(userID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS advisorProfile (
    advisorID     INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(160) NOT NULL,
    catalog       VARCHAR(32),
    status        ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    createdWhen   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS advisorAdviseeBridge (
    advisorID  INT NOT NULL,
    adviseeID  INT NOT NULL,
    isActive   BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (advisorID, adviseeID),
    CONSTRAINT fkadvisor  FOREIGN KEY (advisorID) REFERENCES advisorProfile(advisorID),
    CONSTRAINT fkadvisee  FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID)
);

CREATE TABLE IF NOT EXISTS terms (
    termID      INT PRIMARY KEY,
    code        VARCHAR(32) NOT NULL,
    startDate   DATETIME NOT NULL,
    endDate     DATETIME NOT NULL,
    CONSTRAINT  checkTerm CHECK (endDate > startDate)
);

CREATE TABLE IF NOT EXISTS courses (
    courseID        INT PRIMARY KEY,
    courseName      VARCHAR(160) NOT NULL,
    description     TEXT,
    credits         INT NOT NULL,
    CONSTRAINT checkCredits CHECK (credits > 0)
);

CREATE TABLE IF NOT EXISTS section (
    sectionID       INT PRIMARY KEY,
    courseID        INT NOT NULL,
    termID          INT NOT NULL,
    crn             VARCHAR(32) NOT NULL UNIQUE,
    capacity        INT NOT NULL,
    enrolled        INT NOT NULL DEFAULT 0,
    professorName   VARCHAR(160),
    status          ENUM('OPEN','CLOSED') NOT NULL DEFAULT 'OPEN',
    description     TEXT,
    CONSTRAINT sectionCourses FOREIGN KEY (courseID) REFERENCES courses(courseID),
    CONSTRAINT sectionTerm FOREIGN KEY (termID) REFERENCES terms(termID),
    CONSTRAINT enrolledCapacity CHECK (enrolled <= capacity)
);

CREATE TABLE IF NOT EXISTS schedules (
    scheduleID      INT PRIMARY KEY, 
    adviseeID       INT NOT NULL,
    termID          INT NOT NULL,
    source          VARCHAR(32) NOT NULL,
    status          ENUM('DRAFT','APPROVED','REJECTED') NOT NULL DEFAULT 'DRAFT',
    createdWhen     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approvedWhen    DATETIME,
    rejectedWhen    DATETIME,
    CONSTRAINT scheduleAdvisee FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID),
    CONSTRAINT scheduleTerm FOREIGN KEY (termID) REFERENCES terms(termID),
    CONSTRAINT scheduleDate CHECK (
        (approvedWhen IS NULL OR approvedWhen >= createdWhen) AND 
        (rejectedWhen IS NULL OR rejectedWhen >= createdWhen)
    )
);

CREATE TABLE IF NOT EXISTS classes (
    classID     INT PRIMARY KEY, 
    sectionID   INT NOT NULL,
    scheduleID  INT NOT NULL,
    createdDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT classSection FOREIGN KEY (sectionID) REFERENCES section(sectionID),
    CONSTRAINT classSchedule FOREIGN KEY (scheduleID) REFERENCES schedules(scheduleID),
    UNIQUE KEY scheduleSection(scheduleID, sectionID)
);

CREATE TABLE IF NOT EXISTS enrollments (
    enrollmentID    INT PRIMARY KEY, 
    adviseeID       INT NOT NULL,
    sectionID       INT NOT NULL,
    courseID        INT NOT NULL,
    status          ENUM('ENROLLED','DROPPED') NOT NULL DEFAULT 'ENROLLED',
    grade           VARCHAR(8),
    creditsEarned   INT NOT NULL,
    attemptedNumber INT NOT NULL,
    createdWhen     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT enrolledAdvisee FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID),
    CONSTRAINT enrolledSection FOREIGN KEY (sectionID) REFERENCES section(sectionID),
    CONSTRAINT enrolledCourse  FOREIGN KEY (courseID) REFERENCES courses(courseID),
    CONSTRAINT enrollAdviseeSection UNIQUE (adviseeID, sectionID)
);

CREATE TABLE IF NOT EXISTS notifications (
    notificationID  INT PRIMARY KEY,
    userID          INT NOT NULL,
    description     VARCHAR(500) NOT NULL,
    createdAt       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT notificationUser FOREIGN KEY (userID) REFERENCES users(userID)
);

CREATE TABLE IF NOT EXISTS degreePlan (
    degreePlanID    INT AUTO_INCREMENT PRIMARY KEY,
    adviseeID       INT NOT NULL,
    name            VARCHAR(120) NOT NULL,
    catalog         VARCHAR(20) NOT NULL,
    status          ENUM('Draft','Active','Archived') NOT NULL DEFAULT 'Draft',
    createdWhen     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updatedWhen     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fkDegreePlanAdvisee FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID)
);
