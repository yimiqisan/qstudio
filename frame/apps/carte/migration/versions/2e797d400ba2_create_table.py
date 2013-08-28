"""create table

Revision ID: 2e797d400ba2
Revises: None
Create Date: 2013-08-28 15:19:31.385410

"""

# revision identifiers, used by Alembic.
revision = '2e797d400ba2'
down_revision = None

from alembic import op
import sqlalchemy as sa

from sqlalchemy.sql import expression


def upgrade():
    op.create_table(u'channel',
        sa.Column('id', sa.Integer(),
            nullable=False, primary_key=True, autoincrement=False),
        sa.Column('ukey_author',
            sa.CHAR(length=6), nullable=False, index=True),
        sa.Column('name', sa.Unicode(length=256), nullable=False),
        sa.Column('introduction', sa.Unicode(length=1024), nullable=False),
        sa.Column('template', sa.CHAR(length=128), nullable=False, index=True),
        sa.Column('sort_score', sa.Integer(), nullable=False),
        sa.Column('is_public', sa.Boolean(), server_default=expression.true(),
            nullable=True, index=True),
        sa.Column('date_created', sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.current_timestamp(), index=True),
        sa.UniqueConstraint('ukey', 'name'),
    )
    op.create_table(u'channel_statistics',
        sa.Column('id', sa.Integer(), nullable=False,
            primary_key=True, autoincrement=False),
        sa.Column('shows_count', sa.Integer(),
            server_default='0', nullable=False),
    )
    op.create_table(u'show',
        sa.Column('id', sa.Integer(), nullable=False,
            primary_key=True, autoincrement=False),
        sa.Column('chanel_id', sa.Integer(), sa.ForeignKey('channel.id'),
            nullable=False, index=True),
        sa.Column('title', sa.Unicode(length=256), nullable=False),
        sa.Column('date_created', sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.current_timestamp(), index=True),
    )
    op.create_table(u'show_markdown',
        sa.Column('id', sa.Integer(), autoincrement=False,
            nullable=False, primary_key=True),
        sa.Column('markdown', sa.UnicodeText(),
            server_default=u'', nullable=False),
    )


def downgrade():
    op.drop_table(u'channel')
    op.drop_table(u'channel_statistics')
    op.drop_table(u'show')
    op.drop_table(u'show_markdown')
