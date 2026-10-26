from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import User
from app.schemas import Token, UserCreate, UserRead
from app.security import DUMMY_HASH, Database, create_access_token, password_hash

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Database):
    user = User(username=data.username, email=str(data.email), hashed_password=password_hash.hash(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already registered") from None
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: Database):
    user = db.scalar(select(User).where(User.username == form.username))
    valid = password_hash.verify(form.password, user.hashed_password if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(status_code=401, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    return Token(access_token=create_access_token(user.id))
