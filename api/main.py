from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = 'mysql+pymysql://root:pass@adviseme-db/adviseme'
engine = create_engine(DATABASE_URL)


app = FastAPI()
@app.get("/db")
def index():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            return{"result": result.scalar()}
    except Exception as e:
        return{"result": f"Error connecting to database: {e}"}

@app.get("/")
async def read_root():
    return {"message": "Hello from FastAPI in Docker!"}



Base = declarative_base()

class Students(Base):
    __tablename__ = "students"

    studentID = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    email = Column(String, index=True)



SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/db/students")
def read_items(db: Session = Depends(get_db)):
    items = db.query(Students).all()
    return items
