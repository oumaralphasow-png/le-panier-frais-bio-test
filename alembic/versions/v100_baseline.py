"""V100 baseline schema for Le Panier Frais Bio.

Creates all tables missing from the current metadata. This is intentionally
idempotent for the existing pre-Alembic candidate database: SQLAlchemy
create_all(checkfirst=True) preserves existing tables and creates missing ones.
Future structural changes should use explicit Alembic operations.
"""
from alembic import op

revision = "v100_baseline"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    from app import Base
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)

def downgrade():
    # Baseline downgrade intentionally does not drop business data.
    pass
