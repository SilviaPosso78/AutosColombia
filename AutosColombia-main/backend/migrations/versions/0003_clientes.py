"""Crea clientes y permite asociarlos con varios vehículos.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cliente",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("documento", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("telefono", sa.Text(), nullable=False),
        sa.Column("correo", sa.Text(), nullable=True),
        sa.UniqueConstraint("documento", name="uq_cliente_documento"),
        sa.CheckConstraint("documento ~ '[^[:space:]]'", name="ck_cliente_documento_no_vacio"),
        sa.CheckConstraint(
            "documento = upper(regexp_replace(documento, '^[[:space:]]+|[[:space:]]+$', '', 'g'))",
            name="ck_cliente_documento_normalizado",
        ),
        sa.CheckConstraint("nombre ~ '[^[:space:]]'", name="ck_cliente_nombre_no_vacio"),
        sa.CheckConstraint("telefono ~ '[^[:space:]]'", name="ck_cliente_telefono_no_vacio"),
    )
    op.add_column("vehiculo", sa.Column("cliente_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_vehiculo_cliente",
        "vehiculo",
        "cliente",
        ["cliente_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_vehiculo_cliente_id", "vehiculo", ["cliente_id"])


def downgrade() -> None:
    op.drop_index("ix_vehiculo_cliente_id", table_name="vehiculo")
    op.drop_constraint("fk_vehiculo_cliente", "vehiculo", type_="foreignkey")
    op.drop_column("vehiculo", "cliente_id")
    op.drop_table("cliente")
