import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from functools import lru_cache
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_engine
from app.models import Operador, Sesion, Usuario
from app.schemas.auth import UsuarioCrear, UsuarioRespuesta

COOKIE_NAME = "autos_sesion"
SESSION_SECONDS = 8 * 60 * 60


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=131072, r=8, p=1, maxmem=268435456)
    return f"scrypt$131072$8$1${salt}${digest.hex()}"


@lru_cache(maxsize=1)
def dummy_password_hash() -> str:
    return hash_password(secrets.token_urlsafe(32))


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if (algorithm, n, r, p) != ("scrypt", "131072", "8", "1"):
            return False
        return hmac.compare_digest(hash_password(password, salt).split("$")[-1], expected)
    except (ValueError, TypeError):
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def comprobar_origen(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    if request.headers.get("sec-fetch-site") == "cross-site" or (
        origin and urlsplit(origin).netloc.lower() != request.headers.get("host", "").lower()
    ):
        raise HTTPException(403, "Origen de la solicitud no permitido.")


def usuario_actual(request: Request) -> UsuarioRespuesta:
    comprobar_origen(request)
    token = request.cookies.get(COOKIE_NAME)
    if not token or len(token) > 200:
        raise HTTPException(401, "Inicia sesión para continuar.")
    try:
        # Esta lectura no inicia una transacción en la sesión de los servicios de negocio.
        with Session(get_engine()) as session:
            usuario = session.scalar(select(Usuario).join(Sesion, Sesion.usuario_id == Usuario.id).where(
                Sesion.token_hash == token_digest(token), Sesion.revocada_en.is_(None),
                Sesion.vence_en > datetime.now(timezone.utc), Usuario.activo.is_(True),
            ))
            if usuario is None:
                raise HTTPException(401, "La sesión venció o fue revocada. Inicia sesión nuevamente.")
            return UsuarioRespuesta.model_validate(usuario)
    except SQLAlchemyError:
        raise HTTPException(503, "No se pudo verificar la sesión. Comprueba la base de datos.") from None


UsuarioActual = Annotated[UsuarioRespuesta, Depends(usuario_actual)]


def administrador(usuario: UsuarioActual) -> UsuarioRespuesta:
    if usuario.rol != "ADMINISTRADOR":
        raise HTTPException(403, "Esta operación requiere un administrador.")
    return usuario


def operador(usuario: UsuarioActual) -> UsuarioRespuesta:
    if usuario.rol != "OPERADOR":
        raise HTTPException(403, "Esta operación requiere un operador.")
    return usuario


def crear_usuario(session: Session, data: UsuarioCrear) -> UsuarioRespuesta:
    if data.rol == "OPERADOR" and data.operador_id is None and not data.telefono:
        raise HTTPException(422, "El operador requiere teléfono o un perfil existente.")
    if data.rol == "ADMINISTRADOR" and data.operador_id is not None:
        raise HTTPException(422, "Un administrador no lleva perfil de operador.")
    try:
        with session.begin():
            perfil_id = data.operador_id
            if data.rol == "OPERADOR":
                if perfil_id is not None:
                    perfil = session.get(Operador, perfil_id)
                    if perfil is None:
                        raise HTTPException(404, "Perfil de operador no encontrado.")
                else:
                    perfil = Operador(nombre=data.nombre, telefono=data.telefono)
                    session.add(perfil)
                    session.flush()
                    perfil_id = perfil.id
            cuenta = Usuario(usuario=data.usuario, nombre=data.nombre, rol=data.rol,
                             password_hash=hash_password(data.password.get_secret_value()),
                             operador_id=perfil_id, activo=True)
            session.add(cuenta)
            session.flush()
            return UsuarioRespuesta.model_validate(cuenta)
    except IntegrityError:
        raise HTTPException(409, "El usuario o el perfil de operador ya está registrado.") from None
    except SQLAlchemyError:
        raise HTTPException(503, "No se pudo guardar la cuenta de usuario.") from None
