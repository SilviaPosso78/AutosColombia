"""Modelos iniciales. Importar este módulo no crea tablas ni abre conexiones."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Identity, Index, Integer, Numeric, Text, UniqueConstraint, Uuid, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates


class Base(DeclarativeBase):
    pass


def required_text(value: str, attribute: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{attribute} debe ser texto no vacío.")
    return value.strip()


class Cliente(Base):
    __tablename__ = "cliente"
    __table_args__ = (
        UniqueConstraint("documento", name="uq_cliente_documento"),
        CheckConstraint("documento ~ '[^[:space:]]'", name="ck_cliente_documento_no_vacio"),
        CheckConstraint(
            "documento = upper(regexp_replace(documento, '^[[:space:]]+|[[:space:]]+$', '', 'g'))",
            name="ck_cliente_documento_normalizado",
        ),
        CheckConstraint("nombre ~ '[^[:space:]]'", name="ck_cliente_nombre_no_vacio"),
        CheckConstraint("telefono ~ '[^[:space:]]'", name="ck_cliente_telefono_no_vacio"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    documento: Mapped[str] = mapped_column(Text, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    telefono: Mapped[str] = mapped_column(Text, nullable=False)
    correo: Mapped[str | None] = mapped_column(Text, nullable=True)

    vehiculos: Mapped[list["Vehiculo"]] = relationship(
        back_populates="cliente", passive_deletes=True
    )

    @validates("documento", "nombre", "telefono")
    def validate_required_text(self, key: str, value: str) -> str:
        value = required_text(value, key)
        return value.upper() if key == "documento" else value

    @validates("correo")
    def normalize_correo(self, key: str, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("correo debe ser texto.")
        return value.strip().lower() or None


class Vehiculo(Base):
    __tablename__ = "vehiculo"
    __table_args__ = (
        UniqueConstraint("placa", name="uq_vehiculo_placa"),
        CheckConstraint("placa ~ '[^[:space:]]'", name="ck_vehiculo_placa_no_vacia"),
        CheckConstraint("placa = upper(regexp_replace(placa, '^[[:space:]]+|[[:space:]]+$', '', 'g'))", name="ck_vehiculo_placa_normalizada"),
        CheckConstraint("color ~ '[^[:space:]]'", name="ck_vehiculo_color_no_vacio"),
        CheckConstraint("marca ~ '[^[:space:]]'", name="ck_vehiculo_marca_no_vacia"),
        CheckConstraint("modelo BETWEEN 1 AND 9999", name="ck_vehiculo_modelo_anio"),
        CheckConstraint("tipo IN ('MOTO', 'AUTOMOVIL', 'CAMIONETA')", name="ck_vehiculo_tipo"),
        Index("ix_vehiculo_cliente_id", "cliente_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    placa: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(Text, nullable=False)
    modelo: Mapped[int] = mapped_column(Integer, nullable=False)
    marca: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    cliente_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("cliente.id", name="fk_vehiculo_cliente", ondelete="SET NULL"),
        nullable=True,
    )

    cliente: Mapped[Cliente | None] = relationship(back_populates="vehiculos")

    @validates("placa", "color", "marca", "tipo")
    def validate_text(self, key: str, value: str) -> str:
        value = required_text(value, key)
        if key == "placa":
            return value.upper()
        if key == "tipo" and value not in {"MOTO", "AUTOMOVIL", "CAMIONETA"}:
            raise ValueError("tipo debe ser MOTO, AUTOMOVIL o CAMIONETA.")
        return value

    @validates("modelo")
    def validate_modelo(self, key: str, value: int) -> int:
        if type(value) is not int or not 1 <= value <= 9999:
            raise ValueError("modelo debe ser un año entero entre 1 y 9999.")
        return value


class Celda(Base):
    __tablename__ = "celda"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_celda_codigo"),
        CheckConstraint("codigo ~ '[^[:space:]]'", name="ck_celda_codigo_no_vacio"),
        CheckConstraint("codigo = upper(regexp_replace(codigo, '^[[:space:]]+|[[:space:]]+$', '', 'g'))", name="ck_celda_codigo_normalizado"),
        CheckConstraint("tipo ~ '[^[:space:]]'", name="ck_celda_tipo_no_vacio"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)

    @validates("codigo", "tipo")
    def validate_text(self, key: str, value: str) -> str:
        value = required_text(value, key)
        return value.upper() if key == "codigo" else value


class Operador(Base):
    __tablename__ = "operador"
    __table_args__ = (
        CheckConstraint("nombre ~ '[^[:space:]]'", name="ck_operador_nombre_no_vacio"),
        CheckConstraint("telefono ~ '[^[:space:]]'", name="ck_operador_telefono_no_vacio"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    telefono: Mapped[str] = mapped_column(Text, nullable=False)

    @validates("nombre", "telefono")
    def validate_text(self, key: str, value: str) -> str:
        return required_text(value, key)


class Estancia(Base):
    __tablename__ = "estancia"
    __table_args__ = (
        CheckConstraint("salida >= entrada", name="ck_estancia_orden_fechas"),
        CheckConstraint(
            "(salida IS NULL) = (operador_salida_id IS NULL)",
            name="ck_estancia_cierre_completo",
        ),
        Index("uq_estancia_vehiculo_abierta", "vehiculo_id", unique=True,
              postgresql_where=text("salida IS NULL")),
        Index("uq_estancia_celda_abierta", "celda_id", unique=True,
              postgresql_where=text("salida IS NULL")),
        Index("ix_estancia_vehiculo_entrada", "vehiculo_id", "entrada"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    vehiculo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vehiculo.id", name="fk_estancia_vehiculo", ondelete="RESTRICT"), nullable=False
    )
    celda_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("celda.id", name="fk_estancia_celda", ondelete="RESTRICT"), nullable=False
    )
    entrada: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    salida: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    operador_entrada_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("operador.id", name="fk_estancia_operador_entrada", ondelete="RESTRICT"), nullable=False
    )
    operador_salida_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("operador.id", name="fk_estancia_operador_salida", ondelete="RESTRICT"), nullable=True
    )

    vehiculo: Mapped[Vehiculo] = relationship()
    celda: Mapped[Celda] = relationship()
    operador_entrada: Mapped[Operador] = relationship(foreign_keys=[operador_entrada_id])
    operador_salida: Mapped[Operador | None] = relationship(foreign_keys=[operador_salida_id])

    def esta_abierta(self) -> bool:
        return self.salida is None

    def cerrar(self, fecha_salida: datetime, operador: Operador) -> None:
        """Valida y asigna el cierre; el servicio debe gestionar flush y commit."""
        if not self.esta_abierta():
            raise ValueError("La estancia ya está cerrada.")
        if not isinstance(fecha_salida, datetime) or fecha_salida.utcoffset() is None:
            raise ValueError("La fecha de salida debe tener zona horaria.")
        if not isinstance(self.entrada, datetime) or self.entrada.utcoffset() is None:
            raise ValueError("La entrada debe estar cargada y tener zona horaria antes de cerrar.")
        if fecha_salida.astimezone(timezone.utc) < self.entrada.astimezone(timezone.utc):
            raise ValueError("La salida no puede ser anterior a la entrada.")
        if not isinstance(operador, Operador) or operador.id is None:
            raise ValueError("El operador de salida debe tener un id asignado.")
        self.salida = fecha_salida
        self.operador_salida = operador
        self.operador_salida_id = operador.id


class Tiquete(Base):
    __tablename__ = "tiquete"
    __table_args__ = (
        CheckConstraint("tipo_vehiculo IN ('MOTO', 'AUTOMOVIL', 'CAMIONETA')", name="ck_tiquete_tipo"),
        CheckConstraint("puerta = 'Entrada'", name="ck_tiquete_puerta"),
    )

    estancia_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("estancia.id", ondelete="RESTRICT"), primary_key=True
    )
    placa: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_vehiculo: Mapped[str] = mapped_column(Text, nullable=False)
    celda_codigo: Mapped[str] = mapped_column(Text, nullable=False)
    puerta: Mapped[str] = mapped_column(Text, nullable=False, default="Entrada")
    operador_entrada_nombre: Mapped[str] = mapped_column(Text, nullable=False)
    operador_salida_nombre: Mapped[str | None] = mapped_column(Text)
    reconstruido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Pago(Base):
    __tablename__ = "pago"
    __table_args__ = (
        UniqueConstraint("solicitud_id", name="uq_pago_solicitud"),
        UniqueConstraint("vehiculo_id", "inicio", "fin", name="uq_pago_periodo"),
        CheckConstraint("valor > 0", name="ck_pago_valor"),
        CheckConstraint("fin >= inicio", name="ck_pago_periodo"),
        CheckConstraint("tipo_vehiculo IN ('MOTO', 'AUTOMOVIL', 'CAMIONETA')", name="ck_pago_tipo"),
        Index("ix_pago_vehiculo_fin", "vehiculo_id", "fin"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    solicitud_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    vehiculo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("vehiculo.id", ondelete="RESTRICT"), nullable=False)
    cliente_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cliente.id", ondelete="RESTRICT"), nullable=False)
    operador_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("operador.id", ondelete="RESTRICT"), nullable=False)
    tipo_vehiculo: Mapped[str] = mapped_column(Text, nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False)
    inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fin: Mapped[date] = mapped_column(Date, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AvisoMensualidad(Base):
    __tablename__ = "aviso_mensualidad"
    __table_args__ = (
        UniqueConstraint("pago_id", "dias_antes", name="uq_aviso_pago_dias"),
        UniqueConstraint("mensaje_id", name="uq_aviso_mensaje"),
        CheckConstraint("dias_antes IN (0, 5)", name="ck_aviso_dias"),
        CheckConstraint("estado IN ('PENDIENTE', 'EN_PROCESO', 'ACEPTADO', 'ENTREGADO', 'LEIDO', 'ERROR', 'REVISION', 'OMITIDO', 'CANCELADO')", name="ck_aviso_estado"),
        Index("ix_aviso_estado_fecha", "estado", "programado_para"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    pago_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("pago.id", ondelete="RESTRICT"), nullable=False)
    dias_antes: Mapped[int] = mapped_column(Integer, nullable=False)
    programado_para: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(Text, nullable=False, default="PENDIENTE")
    destinatario: Mapped[str | None] = mapped_column(Text)
    mensaje_id: Mapped[str | None] = mapped_column(Text)
    intento_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enviado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    detalle: Mapped[str | None] = mapped_column(Text)


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = (
        UniqueConstraint("usuario", name="uq_usuario_nombre"),
        UniqueConstraint("operador_id", name="uq_usuario_operador"),
        CheckConstraint("rol IN ('ADMINISTRADOR', 'OPERADOR')", name="ck_usuario_rol"),
        CheckConstraint("(rol = 'OPERADOR') = (operador_id IS NOT NULL)", name="ck_usuario_perfil"),
        CheckConstraint("usuario = lower(btrim(usuario)) AND length(usuario) BETWEEN 3 AND 80", name="ck_usuario_nombre"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    usuario: Mapped[str] = mapped_column(Text, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    rol: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    operador_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("operador.id", ondelete="RESTRICT"))


class Sesion(Base):
    __tablename__ = "sesion"
    __table_args__ = (
        CheckConstraint("vence_en > creada_en", name="ck_sesion_vigencia"),
        Index("ix_sesion_usuario", "usuario_id"),
    )

    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vence_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revocada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
