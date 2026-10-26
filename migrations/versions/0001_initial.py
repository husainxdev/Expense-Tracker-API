"""Create users and owner-scoped transactions."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table("transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("type", sa.String(7), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.CheckConstraint("amount > 0", name="positive_amount"),
        sa.CheckConstraint("type IN ('income', 'expense')", name="valid_transaction_type"),
    )
    op.create_index("ix_transactions_owner_id", "transactions", ["owner_id"])
    op.create_index("ix_transactions_category", "transactions", ["category"])


def downgrade():
    op.drop_table("transactions")
    op.drop_table("users")
