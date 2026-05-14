"""fix_embedding_dimension_to_384

Revision ID: 6daf1504e07b
Revises: add_embedding_col
Create Date: 2026-03-14 02:27:33.178243

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '6daf1504e07b'
down_revision: Union[str, Sequence[str], None] = 'add_embedding_col'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change embedding column from vector(1536) to vector(384) to match all-MiniLM-L6-v2 model."""
    # Set search path to include rag_app schema where the vector extension is installed
    op.execute("SET search_path TO rag_app, public;")

    # Drop the existing index (it references the old column type)
    op.execute("""
        DROP INDEX IF EXISTS rag_app.langchain_pg_embedding_embedding_idx;
    """)

    # Change the embedding column dimension from 1536 to 384
    op.execute("""
        ALTER TABLE rag_app.langchain_pg_embedding
        ALTER COLUMN embedding TYPE vector(384);
    """)

    # Recreate the index with the new dimension
    op.execute("""
        CREATE INDEX langchain_pg_embedding_embedding_idx
        ON rag_app.langchain_pg_embedding
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)


def downgrade() -> None:
    """Revert embedding column from vector(384) back to vector(1536)."""
    op.execute("SET search_path TO rag_app, public;")

    # Drop the index
    op.execute("""
        DROP INDEX IF EXISTS rag_app.langchain_pg_embedding_embedding_idx;
    """)

    # Change back to 1536 dimensions
    op.execute("""
        ALTER TABLE rag_app.langchain_pg_embedding
        ALTER COLUMN embedding TYPE vector(1536);
    """)

    # Recreate index
    op.execute("""
        CREATE INDEX langchain_pg_embedding_embedding_idx
        ON rag_app.langchain_pg_embedding
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)
