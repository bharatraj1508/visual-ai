"""dataset ingestion summary: source file count + resultant size

ZIP uploads can expand into many CSVs; store how many files a dataset was
built from and the total size of its Parquet tables so the UI can report
"950 files combined into 12 tables, 38 MB". NULL on rows ingested before
this feature.

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "datasets", sa.Column("source_file_count", sa.Integer(), nullable=True)
    )
    op.add_column("datasets", sa.Column("size_bytes", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("datasets", "size_bytes")
    op.drop_column("datasets", "source_file_count")
