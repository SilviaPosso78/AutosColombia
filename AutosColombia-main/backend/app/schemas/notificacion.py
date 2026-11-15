from datetime import date, datetime

from pydantic import BaseModel


class AvisoRespuesta(BaseModel):
    id: int
    pago_id: int
    placa: str
    cliente_nombre: str
    telefono: str | None
    programado_para: date
    fin: date
    dias_antes: int
    estado: str
    detalle: str | None
    enviado_en: datetime | None
    texto: str


class AvisosPagina(BaseModel):
    items: list[AvisoRespuesta]
    total: int
    offset: int
    limit: int


class ConfiguracionAvisos(BaseModel):
    habilitado: bool
    configurado: bool
    faltantes: list[str]
    dias_anticipacion: int = 5
