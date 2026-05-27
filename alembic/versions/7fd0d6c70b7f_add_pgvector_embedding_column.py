"""add_pgvector_embedding_column

Revision ID: 7fd0d6c70b7f
Revises: 3a13ed6ecf9d
Create Date: 2026-05-27 19:03:50.340861

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '7fd0d6c70b7f'
down_revision: Union[str, Sequence[str], None] = '3a13ed6ecf9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("notes", sa.Column("embedding", Vector(1536), nullable=True))


def downgrade() -> None:
    op.drop_column("notes", "embedding")
    op.execute("DROP EXTENSION IF EXISTS vector")
