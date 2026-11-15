import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, field_validator

from app.models import required_text

Texto = Annotated[str, BeforeValidator(lambda value: required_text(value, "El campo"))]
Documento = Annotated[Texto, AfterValidator(str.upper)]
_CORREO_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def correo_opcional(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("El correo debe ser texto.")
    value = value.strip()
    if not value:
        return None
    if not _CORREO_PATTERN.fullmatch(value):
        raise ValueError("Introduce un correo válido.")
    return value.lower()


CorreoOpcional = Annotated[str | None, BeforeValidator(correo_opcional)]


class ClienteCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documento: Documento
    nombre: Texto
    telefono: Texto
    correo: CorreoOpcional = None


class ClienteActualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documento: Documento | None = None
    nombre: Texto | None = None
    telefono: Texto | None = None
    correo: CorreoOpcional = None

    @field_validator("documento", "nombre", "telefono", mode="before")
    @classmethod
    def reject_null_required_fields(cls, value):
        if value is None:
            raise ValueError("Los campos enviados no pueden ser nulos.")
        return value


class ClienteRespuesta(ClienteCrear):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int


class ClientesPagina(BaseModel):
    items: list[ClienteRespuesta]
    total: int
    offset: int
    limit: int
