from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

#Describes database entities. Represents how data is stored and loaded.

class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    ADVISOR = "ADVISOR"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"

    userID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    isActive = Column(Boolean, nullable=False, default=True)
    createdDate = Column(DateTime, nullable=False, default=func.now())
