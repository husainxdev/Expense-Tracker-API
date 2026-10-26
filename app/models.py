from datetime import date as Date

from sqlalchemy import CheckConstraint, Date as SQLDate, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254))
    hashed_password: Mapped[str] = mapped_column(String(255))
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_amount"),
        CheckConstraint("type IN ('income', 'expense')", name="valid_transaction_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    amount: Mapped[float] = mapped_column(Float)
    type: Mapped[str] = mapped_column(String(7))
    category: Mapped[str] = mapped_column(String(100), index=True)
    date: Mapped[Date] = mapped_column(SQLDate)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    owner: Mapped[User] = relationship(back_populates="transactions")
