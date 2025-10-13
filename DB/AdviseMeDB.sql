create database if not exists advisemeDB;

use advisemeDB;

create table if not exists users (
  userID       INT AUTO_INCREMENT PRIMARY KEY,
  username     VARCHAR(100)  NOT NULL UNIQUE,
  email        VARCHAR(255)  NOT NULL UNIQUE,
  role         ENUM('STUDENT','ADVISOR','ADMIN') NOT NULL,
  isActive     TINYINT(1)    NOT NULL DEFAULT 1,
  createdDate  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT checkRoles CHECK (role IN ('STUDENT','ADVISOR','ADMIN'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


create table if not exists advisorProfile (
  advisorID     INT PRIMARY KEY,
  name          VARCHAR(160) NOT NULL,
  office        VARCHAR(160) NULL,
  createdWhen   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fkAdvisorProfileUser FOREIGN KEY (advisorID)
    REFERENCES users(userID) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

create table if not exists adviseeProfile (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

create table if not exists advisorAdviseeBridge (
  advisorID  INT NOT NULL,
  adviseeID  INT NOT NULL,
  isActive   TINYINT(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (advisorID, adviseeID),
  CONSTRAINT fkBridgeAdvisor  FOREIGN KEY (advisorID) REFERENCES advisorProfile(advisorID) ON DELETE CASCADE,
  CONSTRAINT fkBridgeAdvisee  FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


create table if not exists terms (
  termID     INT AUTO_INCREMENT PRIMARY KEY,
  code       VARCHAR(32) NOT NULL UNIQUE,
  startDate  DATETIME NOT NULL,
  endDate    DATETIME NOT NULL,
  CONSTRAINT checkTerm CHECK (endDate > startDate)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


create table if not exists courses (
  courseID    INT AUTO_INCREMENT PRIMARY KEY,
  courseName  VARCHAR(160) NOT NULL,
  description TEXT,
  credits     INT NOT NULL,
  CONSTRAINT checkCredits CHECK (credits > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

create table if not exists sections (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


create table if not exists schedules (
  scheduleID   INT AUTO_INCREMENT PRIMARY KEY,
  adviseeID    INT NOT NULL,
  termID       INT NOT NULL,
  source       ENUM('USER','ADVISOR','SYSTEM') NOT NULL DEFAULT 'USER',
  status       ENUM('DRAFT','APPROVED','REJECTED') NOT NULL DEFAULT 'DRAFT',
  createdWhen  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  approvedWhen DATETIME NULL,
  rejectedWhen DATETIME NULL,
  CONSTRAINT scheduleAdvisee FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID) ON DELETE CASCADE,
  CONSTRAINT scheduleTerm    FOREIGN KEY (termID)    REFERENCES terms(termID)           ON DELETE RESTRICT,
  CONSTRAINT scheduleDate CHECK (
    (approvedWhen IS NULL OR approvedWhen >= createdWhen) AND
    (rejectedWhen IS NULL OR rejectedWhen >= createdWhen)
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

create table if not exists classes (
  classID      INT AUTO_INCREMENT PRIMARY KEY,
  sectionID    INT NOT NULL,
  scheduleID   INT NOT NULL,
  createdDate  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT classSection  FOREIGN KEY (sectionID)  REFERENCES sections(sectionID)   ON DELETE RESTRICT,
  CONSTRAINT classSchedule FOREIGN KEY (scheduleID) REFERENCES schedules(scheduleID) ON DELETE CASCADE,
  UNIQUE KEY uq_scheduleSection (scheduleID, sectionID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

create table if not exists enrollments (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

create table if not exists notifications (
  notificationID  INT AUTO_INCREMENT PRIMARY KEY,
  userID          INT NOT NULL,
  description     VARCHAR(500) NOT NULL,
  createdAt       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT notificationUser FOREIGN KEY (userID) REFERENCES users(userID) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


create table if not exists degreePlan (
  degreePlanID  INT AUTO_INCREMENT PRIMARY KEY,
  adviseeID     INT NOT NULL,
  name          VARCHAR(120) NOT NULL,
  catalog       VARCHAR(20)  NOT NULL,
  status        ENUM('Draft','Active','Archived') NOT NULL DEFAULT 'Draft',
  createdWhen   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updatedWhen   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fkDegreePlanAdvisee FOREIGN KEY (adviseeID) REFERENCES adviseeProfile(adviseeID) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
