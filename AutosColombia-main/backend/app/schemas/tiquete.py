from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, field_validator


class TiqueteRespuesta(BaseModel):
    numero: str
    estancia_id: int
    placa: str
    tipo_vehiculo: str
    entrada: datetime
    celda_codigo: str
    puerta: Literal["Entrada"]
    operador_id: int
    operador_nombre: str
    reconstruido: bool

    @field_validator("entrada")
    @classmethod
    def fecha_utc(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)


class MovimientoRespuesta(BaseModel):
    estancia_id: int
    tiquete_numero: str
    placa: str
    tipo_vehiculo: str
    movimiento: Literal["ENTRADA", "SALIDA"]
    fecha: datetime
    celda_id: int
    celda_codigo: str
    puerta: str
    operador_id: int
    operador_nombre: str

    @field_validator("fecha")
    @classmethod
    def fecha_utc(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)


class MovimientosPagina(BaseModel):
    items: list[MovimientoRespuesta]
    total: int
    entradas: int
    salidas: int
    offset: int
    limit: int
