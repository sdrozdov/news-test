"""initial schema — articles + analyses

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-14
"""
import sqlalchemy as sa

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("source_name", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "url", name="uq_articles_user_url"),
    )
    op.create_index("ix_articles_url", "articles", ["url"])
    op.create_index("ix_articles_user_id", "articles", ["user_id"])

    op.create_table(
        "analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "sentiment",
            sa.Enum("positive", "neutral", "negative", name="sentiment"),
            nullable=False,
        ),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analyses_article_id", "analyses", ["article_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_analyses_article_id", table_name="analyses")
    op.drop_table("analyses")
    op.drop_index("ix_articles_user_id", table_name="articles")
    op.drop_index("ix_articles_url", table_name="articles")
    op.drop_table("articles")
    sa.Enum(name="sentiment").drop(op.get_bind(), checkfirst=True)
