"""Conserva los datos del tiquete y los nombres responsables de los movimientos.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tiquete",
        sa.Column("estancia_id", sa.BigInteger(), sa.ForeignKey("estancia.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("placa", sa.Text(), nullable=False),
        sa.Column("tipo_vehiculo", sa.Text(), nullable=False),
        sa.Column("celda_codigo", sa.Text(), nullable=False),
        sa.Column("puerta", sa.Text(), nullable=False),
        sa.Column("operador_entrada_nombre", sa.Text(), nullable=False),
        sa.Column("operador_salida_nombre", sa.Text(), nullable=True),
        sa.Column("reconstruido", sa.Boolean(), nullable=False),
        sa.CheckConstraint("tipo_vehiculo IN ('MOTO', 'AUTOMOVIL', 'CAMIONETA')", name="ck_tiquete_tipo"),
        sa.CheckConstraint("puerta = 'Entrada'", name="ck_tiquete_puerta"),
    )
    op.execute(sa.text("""
        INSERT INTO tiquete (
            estancia_id, placa, tipo_vehiculo, celda_codigo, puerta,
            operador_entrada_nombre, operador_salida_nombre, reconstruido
        )
        SELECT e.id, v.placa, v.tipo, c.codigo, 'Entrada', oe.nombre, os.nombre, true
        FROM estancia e
        JOIN vehiculo v ON v.id = e.vehiculo_id
        JOIN celda c ON c.id = e.celda_id
        JOIN operador oe ON oe.id = e.operador_entrada_id
        LEFT JOIN operador os ON os.id = e.operador_salida_id
    """))


def downgrade() -> None:
    op.drop_table("tiquete")
