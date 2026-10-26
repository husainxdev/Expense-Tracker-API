from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import auth, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Expense Tracker API", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(transactions.router)
