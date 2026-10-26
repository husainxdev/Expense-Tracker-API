from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.models import Transaction
from app.schemas import TransactionRead, TransactionType, TransactionWrite
from app.security import CurrentUser, Database

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def owned_transaction(transaction_id: int, user_id: int, db) -> Transaction:
    transaction = db.scalar(select(Transaction).where(Transaction.id == transaction_id, Transaction.owner_id == user_id))
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(data: TransactionWrite, user: CurrentUser, db: Database):
    transaction = Transaction(**data.model_dump(), owner_id=user.id)
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("", response_model=list[TransactionRead])
def get_transactions(user: CurrentUser, db: Database):
    return db.scalars(select(Transaction).where(Transaction.owner_id == user.id).order_by(Transaction.id)).all()


# Static path must precede /{transaction_id}.
@router.get("/filter", response_model=list[TransactionRead])
def filter_transactions(
    user: CurrentUser,
    db: Database,
    type: TransactionType | None = None,
    category: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    minimum_amount: Annotated[float | None, Query(ge=0, allow_inf_nan=False)] = None,
    maximum_amount: Annotated[float | None, Query(ge=0, allow_inf_nan=False)] = None,
):
    if minimum_amount is not None and maximum_amount is not None and minimum_amount > maximum_amount:
        raise HTTPException(status_code=422, detail="minimum_amount must not exceed maximum_amount")
    query = select(Transaction).where(Transaction.owner_id == user.id)
    if type is not None:
        query = query.where(Transaction.type == type)
    if category is not None:
        query = query.where(Transaction.category == category)
    if minimum_amount is not None:
        query = query.where(Transaction.amount >= minimum_amount)
    if maximum_amount is not None:
        query = query.where(Transaction.amount <= maximum_amount)
    return db.scalars(query.order_by(Transaction.id)).all()


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(transaction_id: int, user: CurrentUser, db: Database):
    return owned_transaction(transaction_id, user.id, db)


@router.put("/{transaction_id}", response_model=TransactionRead)
def update_transaction(transaction_id: int, data: TransactionWrite, user: CurrentUser, db: Database):
    transaction = owned_transaction(transaction_id, user.id, db)
    for field, value in data.model_dump().items():
        setattr(transaction, field, value)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: int, user: CurrentUser, db: Database):
    transaction = owned_transaction(transaction_id, user.id, db)
    db.delete(transaction)
    db.commit()
    return {"message": "Transaction deleted successfully"}
