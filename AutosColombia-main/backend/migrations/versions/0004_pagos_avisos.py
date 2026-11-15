"""Pagos manuales por vehículo y avisos de vencimiento por WhatsApp.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pago",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("solicitud_id", sa.Uuid(), nullable=False),
        sa.Column("vehiculo_id", sa.BigInteger(), sa.ForeignKey("vehiculo.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), sa.ForeignKey("cliente.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operador_id", sa.BigInteger(), sa.ForeignKey("operador.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tipo_vehiculo", sa.Text(), nullable=False),
        sa.Column("valor", sa.Numeric(12, 2), nullable=False),
        sa.Column("fecha_pago", sa.Date(), nullable=False),
        sa.Column("inicio", sa.Date(), nullable=False),
        sa.Column("fin", sa.Date(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("solicitud_id", name="uq_pago_solicitud"),
        sa.UniqueConstraint("vehiculo_id", "inicio", "fin", name="uq_pago_periodo"),
        sa.CheckConstraint("valor > 0", name="ck_pago_valor"),
        sa.CheckConstraint("fin >= inicio", name="ck_pago_periodo"),
        sa.CheckConstraint("tipo_vehiculo IN ('MOTO', 'AUTOMOVIL', 'CAMIONETA')", name="ck_pago_tipo"),
    )
    op.create_index("ix_pago_vehiculo_fin", "pago", ["vehiculo_id", "fin"])
    op.create_table(
        "aviso_mensualidad",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("pago_id", sa.BigInteger(), sa.ForeignKey("pago.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("dias_antes", sa.Integer(), nullable=False),
        sa.Column("programado_para", sa.Date(), nullable=False),
        sa.Column("estado", sa.Text(), nullable=False),
        sa.Column("destinatario", sa.Text(), nullable=True),
        sa.Column("mensaje_id", sa.Text(), nullable=True),
        sa.Column("intento_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enviado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detalle", sa.Text(), nullable=True),
        sa.UniqueConstraint("pago_id", "dias_antes", name="uq_aviso_pago_dias"),
        sa.UniqueConstraint("mensaje_id", name="uq_aviso_mensaje"),
        sa.CheckConstraint("dias_antes IN (0, 5)", name="ck_aviso_dias"),
        sa.CheckConstraint("estado IN ('PENDIENTE', 'EN_PROCESO', 'ACEPTADO', 'ENTREGADO', 'LEIDO', 'ERROR', 'REVISION', 'OMITIDO', 'CANCELADO')", name="ck_aviso_estado"),
    )
    op.create_index("ix_aviso_estado_fecha", "aviso_mensualidad", ["estado", "programado_para"])


def downgrade() -> None:
    op.drop_table("aviso_mensualidad")
    op.drop_table("pago")
