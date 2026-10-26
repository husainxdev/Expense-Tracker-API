from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.routers import auth, transactions
from app.security import Database

app = FastAPI(title="Personal Expense Tracker API", version="1.0.0", description="JWT authenticated income and expense tracking with PostgreSQL.")
app.include_router(auth.router)
app.include_router(transactions.router)


@app.get("/health", tags=["Health"])
def health(db: Database):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ok"}
