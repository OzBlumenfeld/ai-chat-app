"""add embedding column to langchain_pg_embedding

Revision ID: add_embedding_col
Revises: 072ddc213ce5
Create Date: 2026-03-13 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'add_embedding_col'
down_revision: Union[str, Sequence[str], None] = '072ddc213ce5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the missing embedding column to langchain_pg_embedding table."""
    # Set search path to include rag_app schema where the vector extension is installed
    op.execute("SET search_path TO rag_app, public;")

    # Add embedding column with vector type (384 dimensions for all-MiniLM-L6-v2 model)
    # This column was missing when the table was moved from public to rag_app schema
    op.execute("""
        ALTER TABLE rag_app.langchain_pg_embedding
        ADD COLUMN IF NOT EXISTS embedding vector(384);
    """)

    # Create an index on the embedding column for faster similarity searches
    op.execute("""
        CREATE INDEX IF NOT EXISTS langchain_pg_embedding_embedding_idx
        ON rag_app.langchain_pg_embedding
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)


def downgrade() -> None:
    """Remove the embedding column and its index."""
    op.execute("""
        DROP INDEX IF EXISTS rag_app.langchain_pg_embedding_embedding_idx;
    """)

    op.execute("""
        ALTER TABLE rag_app.langchain_pg_embedding
        DROP COLUMN IF EXISTS embedding;
    """)
