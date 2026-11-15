"""Cuentas por rol y sesiones revocables.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("usuario", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("rol", sa.Text(), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("operador_id", sa.BigInteger(), sa.ForeignKey("operador.id", ondelete="RESTRICT")),
        sa.UniqueConstraint("usuario", name="uq_usuario_nombre"),
        sa.UniqueConstraint("operador_id", name="uq_usuario_operador"),
        sa.CheckConstraint("rol IN ('ADMINISTRADOR', 'OPERADOR')", name="ck_usuario_rol"),
        sa.CheckConstraint("(rol = 'OPERADOR') = (operador_id IS NOT NULL)", name="ck_usuario_perfil"),
        sa.CheckConstraint("usuario = lower(btrim(usuario)) AND length(usuario) BETWEEN 3 AND 80", name="ck_usuario_nombre"),
    )
    op.create_table(
        "sesion",
        sa.Column("token_hash", sa.Text(), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), sa.ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocada_en", sa.DateTime(timezone=True)),
        sa.CheckConstraint("vence_en > creada_en", name="ck_sesion_vigencia"),
    )
    op.create_index("ix_sesion_usuario", "sesion", ["usuario_id"])


def downgrade() -> None:
    op.drop_table("sesion")
    op.drop_table("usuario")
