from sqlalchemy import create_engine, text
from fastapi import FastAPI, HTTPException

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

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}
