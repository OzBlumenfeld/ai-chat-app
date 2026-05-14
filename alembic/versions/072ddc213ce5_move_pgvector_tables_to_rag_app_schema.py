"""move_pgvector_tables_to_rag_app_schema

Revision ID: 072ddc213ce5
Revises: ec29eee49eb2
Create Date: 2026-03-13 19:10:30.389575

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '072ddc213ce5'
down_revision: Union[str, Sequence[str], None] = 'ec29eee49eb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Move pgvector tables from public schema to rag_app schema."""
    # Move langchain_pg_collection table if it exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename = 'langchain_pg_collection'
            ) THEN
                ALTER TABLE public.langchain_pg_collection SET SCHEMA rag_app;
            END IF;
        END $$;
    """)

    # Move langchain_pg_embedding table if it exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename = 'langchain_pg_embedding'
            ) THEN
                ALTER TABLE public.langchain_pg_embedding SET SCHEMA rag_app;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Move pgvector tables back to public schema."""
    # Move langchain_pg_collection table back
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT FROM pg_tables
                WHERE schemaname = 'rag_app'
                AND tablename = 'langchain_pg_collection'
            ) THEN
                ALTER TABLE rag_app.langchain_pg_collection SET SCHEMA public;
            END IF;
        END $$;
    """)

    # Move langchain_pg_embedding table back
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT FROM pg_tables
                WHERE schemaname = 'rag_app'
                AND tablename = 'langchain_pg_embedding'
            ) THEN
                ALTER TABLE rag_app.langchain_pg_embedding SET SCHEMA public;
            END IF;
        END $$;
    """)
