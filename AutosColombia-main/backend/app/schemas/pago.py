from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.vehiculo import Identificador, Placa

EstadoMensualidad = Literal["SIN_MENSUALIDAD", "PROGRAMADA", "VIGENTE", "POR_VENCER", "VENCIDA"]


class PagoCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    solicitud_id: UUID
    placa: Placa
    operador_id: Identificador
    valor: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)]
    fecha_pago: date
    inicio: date
    fin: date

    @model_validator(mode="after")
    def validar_periodo(self):
        if self.fin < self.inicio:
            raise ValueError("La fecha final debe ser igual o posterior al inicio.")
        return self


class PagoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    solicitud_id: UUID
    vehiculo_id: int
    cliente_id: int
    operador_id: int
    tipo_vehiculo: str
    valor: Decimal
    fecha_pago: date
    inicio: date
    fin: date
    creado_en: datetime


class PagoListado(PagoRespuesta):
    placa: str
    cliente_nombre: str
    operador_nombre: str


class PagosPagina(BaseModel):
    items: list[PagoListado]
    total: int
    offset: int
    limit: int


class MensualidadRespuesta(BaseModel):
    vehiculo_id: int
    placa: str
    tipo: str
    tarifa_mensual: Decimal
    cliente_id: int | None
    cliente_nombre: str | None
    telefono: str | None
    pago_id: int | None
    inicio: date | None
    fin: date | None
    dias_restantes: int | None
    estado: EstadoMensualidad


class MensualidadesPagina(BaseModel):
    items: list[MensualidadRespuesta]
    total: int
    offset: int
    limit: int
