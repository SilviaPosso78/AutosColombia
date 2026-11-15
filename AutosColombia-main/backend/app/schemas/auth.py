from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, SecretStr, field_validator

from app.models import required_text

NombreUsuario = Annotated[
    str,
    BeforeValidator(lambda value: required_text(value, "Usuario").lower()),
    Field(min_length=3, max_length=80, pattern=r"^[a-z0-9_.-]+$"),
]
Texto = Annotated[str, BeforeValidator(lambda value: required_text(value, "El campo")), Field(max_length=200)]
Rol = Literal["ADMINISTRADOR", "OPERADOR"]


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    usuario: NombreUsuario
    password: SecretStr

    @field_validator("password")
    @classmethod
    def validar_password(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip() or len(value.get_secret_value()) > 128:
            raise ValueError("Introduce una contraseña entre 1 y 128 caracteres.")
        return value


class UsuarioCrear(Login):
    nombre: Texto
    rol: Rol
    telefono: Texto | None = None
    operador_id: Annotated[int | None, Field(ge=1)] = None

    @field_validator("password")
    @classmethod
    def longitud_password(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")
        return value


class UsuarioRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    usuario: str
    nombre: str
    rol: Rol
    activo: bool
    operador_id: int | None


class UsuariosPagina(BaseModel):
    items: list[UsuarioRespuesta]
    total: int
    offset: int
    limit: int


class PasswordCambiar(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    password_actual: SecretStr
    password_nueva: SecretStr

    @field_validator("password_actual", "password_nueva")
    @classmethod
    def validar_password(cls, value: SecretStr, info) -> SecretStr:
        raw = value.get_secret_value()
        minimum = 8 if info.field_name == "password_nueva" else 1
        if not raw.strip() or not minimum <= len(raw) <= 128:
            raise ValueError(f"La contraseña debe tener entre {minimum} y 128 caracteres.")
        return value
