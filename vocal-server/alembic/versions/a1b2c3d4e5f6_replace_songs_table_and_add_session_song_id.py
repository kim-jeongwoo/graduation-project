"""replace songs table and add session.song_id

Revision ID: a1b2c3d4e5f6
Revises: 3a6386a215ec
Create Date: 2026-05-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '3a6386a215ec'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 기존 songs 테이블 제거 (잔나비 데이터 1행 포함, UUID PK 구조)
    op.drop_table('songs')

    # 2. 새 songs 테이블 생성 (String PK, 노래방 자유곡 메타)
    op.create_table(
        'songs',
        sa.Column('id', sa.String(8), primary_key=True),
        sa.Column('artist', sa.String(255), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('master_filename', sa.String(255), nullable=True),
        sa.Column('mr_filename', sa.String(255), nullable=True),
        sa.Column('master_duration_sec', sa.Float(), nullable=True),
        sa.Column('mr_duration_sec', sa.Float(), nullable=True),
        sa.Column('lrc_offset_sec', sa.Float(), nullable=True),
        sa.Column('alignment_status', sa.String(20), nullable=True),
        sa.Column('has_lrc', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_pitch_guide', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )

    # 3. sessions 테이블에 song_id 컬럼 + FK 추가
    op.add_column(
        'sessions',
        sa.Column('song_id', sa.String(8), nullable=True),
    )
    op.create_foreign_key(
        'fk_sessions_song_id',
        'sessions', 'songs',
        ['song_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    # 1. sessions.song_id FK + 컬럼 제거
    op.drop_constraint('fk_sessions_song_id', 'sessions', type_='foreignkey')
    op.drop_column('sessions', 'song_id')

    # 2. 새 songs 테이블 제거
    op.drop_table('songs')

    # 3. 기존 songs 테이블 복원 (UUID PK, 보컬 분석용 구조)
    op.create_table(
        'songs',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('artist', sa.String(), nullable=False),
        sa.Column('duration_sec', sa.Float(), nullable=True),
        sa.Column('mp3_path', sa.String(), nullable=False),
        sa.Column('vocals_path', sa.String(), nullable=True),
        sa.Column('lyrics_path', sa.String(), nullable=True),
        sa.Column('pitch_path', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
