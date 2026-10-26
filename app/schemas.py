from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Category = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
TransactionType = Literal["income", "expense"]
# API accepts JSON numbers; PostgreSQL stores exact cents using NUMERIC(14, 2).
Amount = Annotated[float, Field(gt=0, ge=0.01, le=999999999999.99, allow_inf_nan=False, multiple_of=0.01)]


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: Username
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TransactionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Title
    amount: Amount
    type: TransactionType
    category: Category
    date: date


class TransactionRead(TransactionWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: int
