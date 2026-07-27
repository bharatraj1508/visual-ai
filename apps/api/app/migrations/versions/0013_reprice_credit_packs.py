"""reprice credit packs: 1 credit ~= Rs 1 (was ~Rs 5)

Drops the per-report price ~5x while keeping ~90%+ margin (serving cost is
~Rs 0.65/report). Only updates the pack catalog for FUTURE purchases; existing
balances and completed purchases are untouched.

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (slug, base_credits, bonus_credits, price_minor in paise)
NEW = [
    ("starter", 100, 0, 9900),      # Rs 99
    ("analyst", 300, 50, 29900),    # Rs 299  -> 350 credits
    ("pro", 750, 150, 69900),       # Rs 699  -> 900 credits
    ("studio", 2000, 600, 199900),  # Rs 1999 -> 2600 credits
]
# previous values, for downgrade
OLD = [
    ("starter", 100, 0, 49900),
    ("analyst", 300, 30, 129900),
    ("pro", 750, 125, 279900),
    ("studio", 2000, 500, 699900),
]

_packs = sa.table(
    "credit_packs",
    sa.column("slug", sa.String()),
    sa.column("base_credits", sa.Integer()),
    sa.column("bonus_credits", sa.Integer()),
    sa.column("price_minor", sa.Integer()),
)


def _apply(rows) -> None:
    for slug, base, bonus, price in rows:
        op.execute(
            _packs.update()
            .where(_packs.c.slug == slug)
            .values(base_credits=base, bonus_credits=bonus, price_minor=price)
        )


def upgrade() -> None:
    _apply(NEW)


def downgrade() -> None:
    _apply(OLD)
