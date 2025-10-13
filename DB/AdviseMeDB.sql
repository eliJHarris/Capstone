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

create table if not exists adviseeProfile (
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
    
    CONSTRAINT fk_advisee_user FOREIGN KEY (user_id)
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_advisee_advisor FOREIGN KEY (advisor_id)
        REFERENCES advisors(advisor_id) ON DELETE SET NULL
);

create table if not exists advisorAdviseeBridge (
  advisorID  INT NOT NULL,
  adviseeID  INT NOT NULL,
  isActive   BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (advisorID, adviseeID),
  CONSTRAINT fkadvisor  FOREIGN KEY (advisorID) REFERENCES AdvisorProfile(advisorID),
  CONSTRAINT fkadvisee  FOREIGN KEY (adviseeID) REFERENCES AdviseeProfile(adviseeID)
);


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

create table if not exists degreePlan(
    degreePlanID    INT AUTO_INCREMENT PRIMARY KEY,
    adviseeID       INT NOT NULL,
    name            VARCHAR(120) NOT NULL,
    catalog         VARCHAR(20) NOT NULL,
    status          ENUM('Draft', 'Active', 'Archived') NOT NULL DEFAULT 'DRAFT',
    createdWhen     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updatedWhen     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fkDegreePlanAdvisee FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID)

)